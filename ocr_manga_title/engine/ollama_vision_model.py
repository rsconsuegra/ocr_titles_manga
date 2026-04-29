"""Ollama vision-language OCR model — sends images to multimodal Ollama models."""

from __future__ import annotations

import logging
import time

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult
from ocr_manga_title.services.ollama import chat_completion_sync, is_ollama_configured

logger = logging.getLogger(__name__)

_VISION_CONFIDENCE = 0.8


class OllamaVisionModel(BaseOCRModel):
    """OCR adapter for Ollama multimodal models via the native /api/chat endpoint."""

    def __init__(self, config: ModelConfig):
        self._config = config

    @property
    def name(self) -> str:
        return "ollama_vision"

    @property
    def is_available(self) -> bool:
        return is_ollama_configured()

    def run(self, image_path: str) -> OCRResult:
        self._validate_image_path(image_path)

        if not self.is_available:
            raise ModelNotAvailableError("Ollama not configured (set OLLAMA_BASE_URL)")

        params = self._config.parameters or {}

        from ocr_manga_title.services.config_live import get_ollama_default_vision_model

        model_name = params.get("model_name") or get_ollama_default_vision_model() or "llava"
        prompt = params.get("prompt", "Extract all text from this image.")
        temperature = float(params.get("temperature", 0.1))

        start = time.monotonic()
        try:
            b64 = self._encode_image(image_path)
            result = chat_completion_sync(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                images=[b64],
                temperature=temperature,
            )

            raw_text = result.get("message", {}).get("content", "")
            elapsed_ms = int((time.monotonic() - start) * 1000)

            return OCRResult(
                raw_text=raw_text,
                model_name=self.name,
                confidence=_VISION_CONFIDENCE if raw_text else 0.0,
                processing_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning("Ollama vision error for %s: %s", image_path, e)
            return self._make_error_result(str(e), elapsed_ms)
