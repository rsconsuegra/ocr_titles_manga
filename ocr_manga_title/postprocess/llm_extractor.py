"""LLM-based extraction of structured manga metadata from raw OCR text."""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from ocr_manga_title.exceptions import LLMExtractionError
from ocr_manga_title.schemas import ExtractedTitle, OpenRouterConfig

logger = logging.getLogger(__name__)

_FALLBACK_PROMPT = (
    "You are a manga metadata extraction assistant. Extract title_en, title_ja, code, and confidence "
    'from the raw OCR text. Respond with JSON only: {"title_en": "...", "title_ja": "...", '
    '"code": "...", "confidence": 0.0}. Set null for fields you cannot determine.'
)


class LLMExtractor:
    """Extracts structured manga title metadata from raw OCR text using an LLM.

    Communicates with an OpenAI-compatible API (OpenRouter) and parses the
    JSON response into :class:`~ocr_manga_title.schemas.ExtractedTitle`.
    """

    def __init__(self, config: OpenRouterConfig, prompt_path: str | Path | None = None):
        import openai

        self._client = openai.OpenAI(
            api_key=config.api_key.get_secret_value(),
            base_url=config.base_url,
            timeout=config.request_timeout,
            max_retries=config.max_retries,
        )
        self._model = config.default_model
        self._timeout = config.request_timeout
        if prompt_path:
            self._prompt_path = Path(prompt_path)
        else:
            self._prompt_path = (
                Path(__file__).resolve().parent.parent.parent
                / "prompts"
                / "llm"
                / "extract_title_v1.md"
            )
        self._system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        try:
            return self._prompt_path.read_text().strip()
        except FileNotFoundError:
            logger.warning(
                "Prompt file not found: %s, using fallback", self._prompt_path
            )
            return _FALLBACK_PROMPT

    def extract(self, raw_text: str, model: str | None = None) -> ExtractedTitle:
        """Send raw OCR text to the LLM and parse the structured response.

        Args:
            raw_text: Raw text produced by an OCR model.
            model: Optional override for the LLM model identifier.

        Returns:
            Extracted title metadata.

        Raises:
            LLMExtractionError: If the LLM API call fails or the response
                cannot be parsed as valid JSON.

        """
        import openai as _openai

        model = model or self._model
        start = time.monotonic()

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": raw_text},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                timeout=self._timeout,
            )
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

    def _parse_json(self, content: str) -> dict[str, Any] | None:
        """Parse JSON from the LLM response, tolerating markdown code fences.

        Args:
            content: Raw response string from the LLM.

        Returns:
            Parsed dict, or ``None`` if no valid JSON could be extracted.

        """
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
