"""Placeholder adapter for the GLM-OCR model (not yet implemented)."""

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.schemas import ModelConfig, OCRResult


class GLMOCRModel(BaseOCRModel):
    """Stub adapter for GLM-OCR.  Always reports as unavailable."""

    def __init__(self, config: ModelConfig):
        self._config = config

    @property
    def name(self) -> str:
        """Human-readable identifier for this model."""
        return "glm_ocr"

    @property
    def is_available(self) -> bool:
        """Whether the GLM-OCR runtime dependencies are installed."""
        return False

    def run(self, image_path: str) -> OCRResult:
        """Execute OCR on the given image using GLM-OCR."""
        raise NotImplementedError(f"{self.name} integration not yet implemented")
