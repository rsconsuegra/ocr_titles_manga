"""OCR adapter for Ollama vision models via the native /api/chat endpoint."""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.schemas import ModelConfig, OCRResult

logger = logging.getLogger(__name__)


class OllamaVisionModel(BaseOCRModel):
    """OCR adapter that sends images to an Ollama vision model.

    Uses the native ``/api/chat`` endpoint with base64-encoded images.
    The specific Ollama model is selected via the ``model`` parameter.
    """

    def __init__(self, config: ModelConfig):
        self._config = config

    @property
    def name(self) -> str:
        return "ollama_vision"

    @property
    def is_available(self) -> bool:
        from ocr_manga_title.services.ollama import is_ollama_configured

        params = self._config.parameters or {}
        return is_ollama_configured() and bool(params.get("model_name"))

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def run(self, image_path: str) -> OCRResult:
        from ocr_manga_title.exceptions import ModelNotAvailableError
        from ocr_manga_title.services.ollama import chat_completion_sync

        if not self.is_available:
            raise ModelNotAvailableError(
                "Ollama not configured or no model selected"
            )

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        params = self._config.parameters or {}
        model = params.get("model_name", "")
        prompt = params.get("prompt", "Extract all text from this image.")

        b64 = self._encode_image(image_path)

        start = time.monotonic()
        try:
            result = chat_completion_sync(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                images=[b64],
                temperature=params.get("temperature", 0.1),
            )
            raw_text = result.get("message", {}).get("content", "")
            elapsed_ms = int((time.monotonic() - start) * 1000)

            return OCRResult(
                raw_text=raw_text,
                model_name=f"ollama:{model}",
                confidence=0.8 if raw_text else 0.0,
                processing_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning("Ollama vision OCR error: %s", e)
            return OCRResult(
                raw_text="",
                model_name=f"ollama:{model}",
                confidence=0.0,
                processing_time_ms=elapsed_ms,
                error=str(e),
            )
