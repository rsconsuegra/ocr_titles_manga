"""Abstract base class that all OCR model adapters must implement."""

import base64
from abc import ABC, abstractmethod
from pathlib import Path

from ocr_manga_title.schemas import ModelConfig, OCRResult


class BaseOCRModel(ABC):
    """Interface for OCR model adapters.

    Subclasses must define ``name``, ``is_available``, and :meth:`run`.

    Provides shared helpers for image encoding, path validation, and error
    result construction.
    """

    @abstractmethod
    def __init__(self, config: ModelConfig) -> None:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable identifier for this model."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether the model's runtime dependencies are installed and accessible."""

    @abstractmethod
    def run(self, image_path: str) -> OCRResult:
        """Execute OCR on the given image.

        Args:
            image_path: Path to the image file.

        Returns:
            :class:`~ocr_manga_title.schemas.OCRResult` with raw text and metadata.

        Raises:
            FileNotFoundError: If the image does not exist.
            ModelNotAvailableError: If the model's dependencies are missing.

        """

    def _validate_image_path(self, image_path: str) -> None:
        """Raise ``FileNotFoundError`` if *image_path* does not exist.

        Args:
            image_path: Path to validate.

        Raises:
            FileNotFoundError: If the path does not exist.

        """
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

    @staticmethod
    def _encode_image(image_path: str) -> str:
        """Return the base64-encoded contents of *image_path*."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _make_error_result(self, error: str, elapsed_ms: int = 0) -> OCRResult:
        """Return an :class:`OCRResult` representing a failure."""
        return OCRResult(
            raw_text="",
            model_name=self.name,
            confidence=0.0,
            processing_time_ms=elapsed_ms,
            error=error,
        )

    def warmup(self) -> None:
        """Pre-load model weights so the first real call is fast.

        The default implementation is a no-op.  Subclasses that support
        eager loading (e.g. local OCR models) should override this.
        """
