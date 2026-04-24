"""Abstract base class that all OCR model adapters must implement."""

from abc import ABC, abstractmethod

from ocr_manga_title.schemas import ModelConfig, OCRResult


class BaseOCRModel(ABC):
    """Interface for OCR model adapters.

    Subclasses must define ``name``, ``is_available``, and :meth:`run`.
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
