"""Adapter wrapping any OpenAI-compatible vision API for OCR."""

from pathlib import Path

from openai import OpenAI

from ocr_manga_title.engine.base import VISION_CONFIDENCE, BaseOCRModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult

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
        """Initialize the vision API OCR adapter.

        Args:
            config: Model configuration including API endpoint and credentials.

        """
        super().__init__(config)
        self._client: OpenAI | None = None

    @property
    def name(self) -> str:
        """Machine-readable identifier for this model."""
        return "glm_ocr"

    @property
    def is_available(self) -> bool:
        """Whether this model's runtime dependencies are installed."""
        params = self._config.parameters or {}
        return bool(params.get("api_endpoint"))

    def _get_client(self) -> OpenAI:
        if self._client is None:
            import openai

            params = self._config.parameters or {}
            self._client = openai.OpenAI(
                base_url=params.get("api_endpoint", ""),
                api_key=params.get("api_key", ""),
            )
        return self._client

    def _do_run(self, image_path: str) -> OCRResult:
        if not self.is_available:
            raise ModelNotAvailableError("Vision API endpoint not configured")

        self._validate_image_path(image_path)

        client = self._get_client()
        params = self._config.parameters or {}

        path = Path(image_path)
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
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                    ],
                }
            ],
            max_tokens=params.get("max_tokens", 4096),
            temperature=params.get("temperature", 0.1),
        )

        raw_text = response.choices[0].message.content or ""

        return OCRResult(
            raw_text=raw_text,
            model_name=self.name,
            confidence=VISION_CONFIDENCE if raw_text else 0.0,
            processing_time_ms=0,
        )
