"""Abstract base class that all OCR model adapters must implement."""

import base64
import importlib.util
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path

from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult

VISION_CONFIDENCE = 0.8


class BaseOCRModel(ABC):
    """Interface for OCR model adapters.

    Subclasses must define ``name``, ``is_available``, and :meth:`_do_run`.

    Provides shared helpers for image encoding, path validation, timing,
    error result construction, and a template method for :meth:`run`.
    """

    _logger: logging.Logger = logging.getLogger(__name__)

    def __init__(self, config: ModelConfig) -> None:
        """Initialize the OCR model adapter.

        Args:
            config: Model configuration including name, enabled flag, and parameters.

        """
        self._config = config
        self._detailed = config.parameters.get("detailed", False)

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable identifier for this model."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether the model's runtime dependencies are installed and accessible."""

    @abstractmethod
    def _do_run(self, image_path: str) -> OCRResult:
        """Execute OCR on the given image (subclass-specific logic).

        Subclasses implement this method with engine-specific OCR logic.
        Timing, error handling, and logging are handled by :meth:`run`.

        Args:
            image_path: Path to the image file.

        Returns:
            :class:`~ocr_manga_title.schemas.OCRResult` with raw text and metadata.

        """

    def run(self, image_path: str) -> OCRResult:
        """Execute OCR on the given image with timing and error handling.

        This is a template method that wraps :meth:`_do_run`.  It measures
        processing time, catches exceptions, and returns error results.

        Args:
            image_path: Path to the image file.

        Returns:
            :class:`~ocr_manga_title.schemas.OCRResult` with raw text and metadata.

        Raises:
            FileNotFoundError: If the image does not exist.
            ModelNotAvailableError: If the model's dependencies are missing.

        """
        start = time.monotonic()
        try:
            result = self._do_run(image_path)
            if result.processing_time_ms == 0:
                result.processing_time_ms = int((time.monotonic() - start) * 1000)
            return result
        except (FileNotFoundError, ModelNotAvailableError):
            raise
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            self._logger.warning("OCR error for %s: %s", image_path, e)
            return self._make_error_result(str(e), elapsed_ms)

    @staticmethod
    def _is_package_installed(package_name: str) -> bool:
        """Return whether a Python package is importable."""
        return importlib.util.find_spec(package_name) is not None

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

    def warmup(self) -> None:  # noqa: B027
        """Pre-load model weights so the first real call is fast.

        The default implementation is a no-op.  Subclasses that support
        eager loading (e.g. local OCR models) should override this.
        """
