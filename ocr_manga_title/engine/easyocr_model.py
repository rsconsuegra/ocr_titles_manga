"""Placeholder adapter for the EasyOCR engine (not yet implemented)."""

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.schemas import ModelConfig, OCRResult


class EasyOCRModel(BaseOCRModel):
    """Stub adapter for EasyOCR.  Always reports as unavailable."""

    def __init__(self, config: ModelConfig):
        self._config = config

    @property
    def name(self) -> str:
        """Human-readable identifier for this model."""
        return "easyocr"

    @property
    def is_available(self) -> bool:
        """Whether the EasyOCR runtime dependencies are installed."""
        return False

    def run(self, image_path: str) -> OCRResult:
        """Execute OCR on the given image using EasyOCR."""
        raise NotImplementedError(f"{self.name} integration not yet implemented")
