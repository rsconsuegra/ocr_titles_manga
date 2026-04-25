"""Adapter wrapping any OpenAI-compatible vision API for OCR."""

import base64
import logging
import time
from pathlib import Path

import openai

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult

logger = logging.getLogger(__name__)

_MIME_MAP = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "tiff": "image/tiff",
    "tif": "image/tiff",
    "bmp": "image/bmp",
}


class GLMOCRModel(BaseOCRModel):
    """OCR adapter for vision-language models via OpenAI-compatible chat completions API.

    Sends images as base64 to any configured endpoint (OpenRouter, ZhipuAI,
    OpenAI, etc.).  No model download required — pure HTTP client.
    """

    def __init__(self, config: ModelConfig):
        self._config = config
        self._client = None

    @property
    def name(self) -> str:
        """Human-readable identifier for this model."""
        return "glm_ocr"

    @property
    def is_available(self) -> bool:
        """Whether a vision API endpoint is configured."""
        params = self._config.parameters or {}
        return bool(params.get("api_endpoint"))

    def _get_client(self) -> openai.OpenAI:
        if self._client is None:
            params = self._config.parameters or {}
            self._client = openai.OpenAI(
                base_url=params.get("api_endpoint", ""),
                api_key=params.get("api_key", ""),
            )
        return self._client

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def run(self, image_path: str) -> OCRResult:
        """Run vision API OCR on the given image.

        Sends the image as base64 via the OpenAI chat completions format.

        Args:
            image_path: Path to the image file.

        Returns:
            :class:`~ocr_manga_title.schemas.OCRResult` with model response as
            raw text and confidence 0.8 for non-empty responses.  On errors,
            returns a result with ``confidence=0.0`` and the error message.

        Raises:
            ModelNotAvailableError: If no API endpoint is configured.
            FileNotFoundError: If the image file does not exist.

        """
        if not self.is_available:
            raise ModelNotAvailableError("Vision API endpoint not configured")

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        start = time.monotonic()
        try:
            client = self._get_client()
            params = self._config.parameters or {}

            ext = path.suffix.lower().lstrip(".")
            mime = _MIME_MAP.get(ext, "image/png")
            b64 = self._encode_image(image_path)

            response = client.chat.completions.create(
                model=params.get("model", "google/gemini-2.5-flash"),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": params.get(
                                    "prompt",
                                    "Extract all text from this image.",
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{b64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=params.get("max_tokens", 4096),
                temperature=params.get("temperature", 0.1),
            )

            raw_text = response.choices[0].message.content or ""
            elapsed_ms = int((time.monotonic() - start) * 1000)

            return OCRResult(
                raw_text=raw_text,
                model_name=self.name,
                confidence=0.8 if raw_text else 0.0,
                processing_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning("Vision API error for %s: %s", image_path, e)
            return OCRResult(
                raw_text="",
                model_name=self.name,
                confidence=0.0,
                processing_time_ms=elapsed_ms,
                error=str(e),
            )
