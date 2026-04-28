"""Adapter wrapping `pytesseract <https://github.com/madmaze/pytesseract>`_ for Tesseract OCR."""

import logging
import time
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult

logger = logging.getLogger(__name__)


class TesseractModel(BaseOCRModel):
    """OCR adapter for Tesseract via the ``pytesseract`` Python bindings.

    Supports configurable PSM/OEM modes and multi-language strings passed
    through the ``languages`` parameter.
    """

    def __init__(self, config: ModelConfig):
        """Initialize the adapter with Tesseract parameters from config.

        Reads ``languages``, ``psm`` (default 3), and ``oem`` (default 3)
        from ``config.parameters``.

        Args:
            config: Per-model configuration including Tesseract-specific parameters.

        """
        self._config = config
        languages = config.parameters.get("languages", ["eng"])
        if isinstance(languages, list):
            self._lang_string = "+".join(languages)
        else:
            self._lang_string = str(languages)
        self._psm = config.parameters.get("psm", 3)
        self._oem = config.parameters.get("oem", 3)
        self._tess_config = f"--psm {self._psm} --oem {self._oem}"
        self._available: bool | None = None

    @property
    def name(self) -> str:
        """Human-readable identifier for this model."""
        return "tesseract"

    @property
    def is_available(self) -> bool:
        """Check whether the ``pytesseract`` package and Tesseract binary are accessible."""
        if self._available is None:
            try:
                import pytesseract

                pytesseract.get_tesseract_version()
                self._available = True
            except Exception:
                self._available = False
        return self._available

    def run(self, image_path: str) -> OCRResult:
        """Run Tesseract OCR on the given image.

        Uses ``image_to_data`` for both text extraction and confidence scoring
        in a single pass, filtering out entries below confidence 30.

        Args:
            image_path: Path to the image file.

        Returns:
            :class:`~ocr_manga_title.schemas.OCRResult` with extracted text and
            averaged confidence.  On unreadable images or runtime errors,
            returns a result with ``confidence=0.0`` and the error message.

        Raises:
            FileNotFoundError: If the image does not exist.
            ModelNotAvailableError: If Tesseract is not installed.

        """
        import pytesseract
        from pytesseract import Output

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if not self.is_available:
            raise ModelNotAvailableError(
                "Tesseract binary not found. Install: brew install tesseract"
            )

        try:
            image = Image.open(path)
            image.load()
        except UnidentifiedImageError as e:
            return OCRResult(
                raw_text="",
                model_name=self.name,
                confidence=0.0,
                processing_time_ms=0,
                error=str(e),
            )

        start = time.monotonic()
        try:
            data = pytesseract.image_to_data(
                image,
                lang=self._lang_string,
                config=self._tess_config,
                output_type=Output.DICT,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)

            texts = []
            confs = []
            for i, text in enumerate(data["text"]):
                conf = int(data["conf"][i])
                if conf >= 0 and text.strip():
                    texts.append(text)
                if conf >= 30:
                    confs.append(conf)

            raw_text = " ".join(texts)
            confidence = sum(confs) / len(confs) / 100.0 if confs else 0.0

            return OCRResult(
                raw_text=raw_text.strip(),
                model_name=self.name,
                confidence=confidence,
                processing_time_ms=elapsed_ms,
            )
        except FileNotFoundError:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            try:
                raw_text = pytesseract.image_to_string(
                    image,
                    lang=self._lang_string,
                    config=self._tess_config,
                ).strip()
                return OCRResult(
                    raw_text=raw_text,
                    model_name=self.name,
                    confidence=0.0,
                    processing_time_ms=elapsed_ms,
                )
            except Exception as fallback_err:
                return OCRResult(
                    raw_text="",
                    model_name=self.name,
                    confidence=0.0,
                    processing_time_ms=elapsed_ms,
                    error=f"image_to_data TSV missing, fallback failed: {fallback_err}",
                )
        except pytesseract.TesseractError as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return OCRResult(
                raw_text="",
                model_name=self.name,
                confidence=0.0,
                processing_time_ms=elapsed_ms,
                error=str(e),
            )
