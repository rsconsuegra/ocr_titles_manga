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


class LLMExtractor:
    """Extracts structured manga title metadata from raw OCR text using an LLM.

    Supports two backends:
      * **openrouter** — OpenAI-compatible API via the ``openai`` client.
      * **ollama** — Native Ollama ``/api/chat`` endpoint via ``httpx``.
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

    def extract(self, raw_text: str, model: str | None = None) -> ExtractedTitle:
        """Send raw OCR text to the LLM and parse the structured response."""
        if self._provider == "ollama":
            return self._extract_ollama(raw_text, model)
        return self._extract_openrouter(raw_text, model)

    def _extract_openrouter(
        self, raw_text: str, model: str | None = None
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

        try:
            create_kwargs: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": temperature,
                "response_format": {"type": "json_object"},
                "timeout": self._timeout,
            }
            if (
                self._prompt_config
                and self._prompt_config.reasoning_enabled
            ):
                create_kwargs["extra_body"] = {"reasoning": {"enabled": True}}
            response = self._openai_client.chat.completions.create(**create_kwargs)
        except _openai.AuthenticationError as e:
            raise LLMExtractionError(f"Authentication error: {e}") from e
        except (_openai.APIError, _openai.APITimeoutError) as e:
            raise LLMExtractionError(f"API error: {e}") from e
        except Exception as e:
            raise LLMExtractionError(f"Unexpected error calling LLM: {e}") from e

        elapsed_ms = int((time.monotonic() - start) * 1000)
        content = response.choices[0].message.content or ""

        if response.usage:
            logger.debug(
                "LLM token usage: prompt=%d, completion=%d, total=%d, latency=%dms",
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                response.usage.total_tokens,
                elapsed_ms,
            )

        parsed = self._parse_json(content)
        if parsed is None:
            raise LLMExtractionError(
                f"Failed to parse LLM response as JSON: {content[:200]}"
            )

        return ExtractedTitle(
            title_en=parsed.get("title_en"),
            title_ja=parsed.get("title_ja"),
            code=parsed.get("code"),
            confidence=float(parsed.get("confidence", 0.0)),
            source_model=model,
            source_method="llm",
        )

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

        try:
            result = chat_completion_sync(
                model=effective_model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_content},
                ],
                format=_EXTRACT_JSON_SCHEMA,
                temperature=temperature,
                timeout=self._ollama_config.timeout,
            )
        except (_httpx.HTTPError, RuntimeError) as e:
            raise LLMExtractionError(f"Ollama API error: {e}") from e

        elapsed_ms = int((time.monotonic() - start) * 1000)
        content = result.get("message", {}).get("content", "")

        logger.debug("Ollama LLM latency=%dms, model=%s", elapsed_ms, effective_model)

        parsed = self._parse_json(content)
        if parsed is None:
            raise LLMExtractionError(
                f"Failed to parse Ollama response as JSON: {content[:200]}"
            )

        return ExtractedTitle(
            title_en=parsed.get("title_en"),
            title_ja=parsed.get("title_ja"),
            code=parsed.get("code"),
            confidence=float(parsed.get("confidence", 0.0)),
            source_model=effective_model,
            source_method="llm",
        )

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
