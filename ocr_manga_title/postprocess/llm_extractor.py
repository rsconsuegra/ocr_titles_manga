"""LLM-based extraction of structured manga metadata from raw OCR text."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from ocr_manga_title.exceptions import LLMExtractionError
from ocr_manga_title.schemas import (
    ExtractedTitle,
    LLMPromptConfig,
    OllamaConfig,
    OpenRouterConfig,
)

logger = logging.getLogger(__name__)

_FALLBACK_PROMPT = (
    "You are a manga metadata extraction assistant. Extract title_en, title_ja, code, and confidence "
    'from the raw OCR text. Respond with JSON only: {"title_en": "...", "title_ja": "...", '
    '"code": "...", "confidence": 0.0}. Set null for fields you cannot determine.'
)

_EXTRACT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title_en": {"type": "string"},
        "title_ja": {"type": "string"},
        "code": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["title_en", "title_ja", "code", "confidence"],
}

_FIELD_ALIASES: dict[str, str] = {
    "manga_name": "title_en",
    "manga_title": "title_en",
    "english_title": "title_en",
    "series_name": "title_en",
    "series_title": "title_en",
    "japanese_title": "title_ja",
    "japanese_name": "title_ja",
    "native_title": "title_ja",
    "original_title": "title_ja",
    "six_digit_number": "code",
    "sauce": "code",
    "source_id": "code",
    "nhentai_code": "code",
}


class LLMExtractor:
    """Extracts structured manga title metadata from raw OCR text using an LLM.

    Supports two backends:
      * **openrouter** -- OpenAI-compatible API via the ``openai`` client.
      * **ollama** -- Native Ollama ``/api/chat`` endpoint via ``httpx``.
    """

    def __init__(
        self,
        openrouter_config: OpenRouterConfig | None = None,
        ollama_config: OllamaConfig | None = None,
        provider: str = "openrouter",
        prompt_path: str | Path | None = None,
        prompt_config: LLMPromptConfig | None = None,
    ):
        self._provider = provider
        self._ollama_config = ollama_config
        self._prompt_config = prompt_config

        if prompt_config and prompt_config.system_prompt:
            self._system_prompt = prompt_config.system_prompt
        elif prompt_path:
            self._prompt_path = Path(prompt_path)
            self._system_prompt = self._load_prompt()
        else:
            self._prompt_path = (
                Path(__file__).resolve().parent.parent.parent
                / "prompts"
                / "llm"
                / "extract_title_v1.md"
            )
            self._system_prompt = self._load_prompt()

        self._openai_client = None
        if provider == "openrouter" and openrouter_config:
            import openai

            self._openai_client = openai.OpenAI(
                api_key=openrouter_config.api_key.get_secret_value(),
                base_url=openrouter_config.base_url,
                timeout=openrouter_config.request_timeout,
                max_retries=openrouter_config.max_retries,
            )
            self._model = openrouter_config.default_model
            self._timeout = openrouter_config.request_timeout

    def _load_prompt(self) -> str:
        try:
            return self._prompt_path.read_text().strip()
        except FileNotFoundError:
            logger.warning("Prompt file not found: %s, using fallback", self._prompt_path)
            return _FALLBACK_PROMPT

    def extract(self, raw_text: str, model: str | None = None, *, supports_json_mode: bool = True) -> ExtractedTitle:
        """Send raw OCR text to the LLM and parse the structured response."""
        if self._provider == "ollama":
            return self._extract_ollama(raw_text, model)
        return self._extract_openrouter(raw_text, model, supports_json_mode=supports_json_mode)

    def _extract_openrouter(
        self, raw_text: str, model: str | None = None, *, supports_json_mode: bool = True
    ) -> ExtractedTitle:
        import openai as _openai

        if not self._openai_client:
            raise LLMExtractionError("OpenRouter client not initialized")

        model = model or self._model
        start = time.monotonic()
        temperature = self._prompt_config.temperature if self._prompt_config else 0.1
        user_content = (
            self._prompt_config.render_user_prompt(raw_text)
            if self._prompt_config
            else raw_text
        )

        base_kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
            "timeout": self._timeout,
        }
        if self._prompt_config and self._prompt_config.reasoning_enabled:
            base_kwargs["extra_body"] = {"reasoning": {"enabled": True}}

        if supports_json_mode:
            content = self._call_openai(base_kwargs, json_mode=True, _openai=_openai)
            if not content.strip():
                logger.warning(
                    "JSON mode returned empty for model=%s, retrying without response_format",
                    model,
                )
                content = self._call_openai(base_kwargs, json_mode=False, _openai=_openai)
        else:
            content = self._call_openai(base_kwargs, json_mode=False, _openai=_openai)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.debug("LLM latency=%dms, model=%s", elapsed_ms, model)

        return self._build_result(content, model)

    def _call_openai(
        self, base_kwargs: dict[str, Any], *, json_mode: bool, _openai: Any
    ) -> str:
        kwargs = {**base_kwargs}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = self._openai_client.chat.completions.create(**kwargs)  # type: ignore[union-attr]
        except _openai.AuthenticationError as e:
            raise LLMExtractionError(f"Authentication error: {e}") from e
        except (_openai.APIError, _openai.APITimeoutError) as e:
            raise LLMExtractionError(f"API error: {e}") from e
        except Exception as e:
            raise LLMExtractionError(f"Unexpected error calling LLM: {e}") from e

        if response.usage:
            logger.debug(
                "LLM token usage: prompt=%d, completion=%d, total=%d",
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                response.usage.total_tokens,
            )

        return response.choices[0].message.content or ""

    def _extract_ollama(
        self, raw_text: str, model: str | None = None
    ) -> ExtractedTitle:
        import httpx as _httpx

        from ocr_manga_title.services.ollama import chat_completion_sync

        if not self._ollama_config:
            raise LLMExtractionError("Ollama config not provided")

        effective_model = model or self._ollama_config.default_model
        start = time.monotonic()
        temperature = self._prompt_config.temperature if self._prompt_config else 0.1
        user_content = (
            self._prompt_config.render_user_prompt(raw_text)
            if self._prompt_config
            else raw_text
        )

        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            result = chat_completion_sync(
                model=effective_model,
                messages=messages,
                format=_EXTRACT_JSON_SCHEMA,
                temperature=temperature,
                timeout=self._ollama_config.timeout,
            )
        except (_httpx.HTTPError, RuntimeError) as e:
            raise LLMExtractionError(f"Ollama API error: {e}") from e

        content = result.get("message", {}).get("content", "")

        if not content.strip():
            logger.warning(
                "Structured output returned empty for Ollama model=%s, retrying without format",
                effective_model,
            )
            try:
                result = chat_completion_sync(
                    model=effective_model,
                    messages=messages,
                    temperature=temperature,
                    timeout=self._ollama_config.timeout,
                )
            except (_httpx.HTTPError, RuntimeError) as e:
                raise LLMExtractionError(f"Ollama API error: {e}") from e
            content = result.get("message", {}).get("content", "")

        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.debug("Ollama LLM latency=%dms, model=%s", elapsed_ms, effective_model)

        return self._build_result(content, effective_model)

    def _build_result(self, content: str, model: str) -> ExtractedTitle:
        logger.info("LLM response: %d chars, model=%s", len(content), model)

        if not content.strip():
            return ExtractedTitle(
                raw_response=content,
                confidence=0.0,
                source_model=model,
                source_method="llm_empty",
            )

        parsed = self._parse_json(content)
        if parsed is None:
            return ExtractedTitle(
                raw_response=content,
                confidence=0.0,
                source_model=model,
                source_method="llm_unparsed",
            )

        normalized = self._normalize_keys(parsed)
        return ExtractedTitle(
            title_en=normalized.get("title_en"),
            title_ja=normalized.get("title_ja"),
            code=normalized.get("code"),
            confidence=float(normalized.get("confidence", 0.0)),
            source_model=model,
            source_method="llm",
            raw_response=content,
        )

    @staticmethod
    def _normalize_keys(parsed: dict[str, Any]) -> dict[str, Any]:
        return {_FIELD_ALIASES.get(k, k): v for k, v in parsed.items()}

    def _parse_json(self, content: str) -> dict[str, Any] | None:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return None
