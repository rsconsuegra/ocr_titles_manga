"""Ollama vision-language OCR model — sends images to multimodal Ollama models."""

from __future__ import annotations

from ocr_manga_title.engine.base import VISION_CONFIDENCE, BaseOCRModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult
from ocr_manga_title.services.ollama import (
    ChatCompletionRequest,
    chat_completion_sync,
    is_ollama_configured,
)


class OllamaVisionModel(BaseOCRModel):
    """OCR adapter for Ollama multimodal models via the native /api/chat endpoint."""

    def __init__(self, config: ModelConfig) -> None:
        """Initialize the Ollama vision adapter.

        Args:
            config: Model configuration including model name and prompt.

        """
        super().__init__(config)

    @property
    def name(self) -> str:
        """Machine-readable identifier for this model."""
        return "ollama_vision"

    @property
    def is_available(self) -> bool:
        """Whether this model's runtime dependencies are installed."""
        return is_ollama_configured()

    def _do_run(self, image_path: str) -> OCRResult:
        self._validate_image_path(image_path)

        if not self.is_available:
            raise ModelNotAvailableError("Ollama not configured (set OLLAMA_BASE_URL)")

        params = self._config.parameters or {}

        from ocr_manga_title.services.config_live import get_ollama_default_vision_model

        model_name = (
            params.get("model_name") or get_ollama_default_vision_model() or "llava"
        )
        prompt = params.get("prompt", "Extract all text from this image.")
        temperature = float(params.get("temperature", 0.1))

        b64 = self._encode_image(image_path)
        result = chat_completion_sync(
            ChatCompletionRequest(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                images=[b64],
                temperature=temperature,
            )
        )

        raw_text = result.get("message", {}).get("content", "")

        return OCRResult(
            raw_text=raw_text,
            model_name=self.name,
            confidence=VISION_CONFIDENCE if raw_text else 0.0,
            processing_time_ms=0,
        )
