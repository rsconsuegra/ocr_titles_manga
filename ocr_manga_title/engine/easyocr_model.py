"""Adapter wrapping EasyOCR for multilingual text detection and recognition."""

import importlib.util
import logging
import os
import time

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult, TextBlock

logger = logging.getLogger(__name__)


class EasyOCRModel(BaseOCRModel):
    """OCR adapter for EasyOCR with lazy reader loading and configurable languages."""

    def __init__(self, config: ModelConfig):
        self._config = config
        self._reader = None
        self._detailed = config.parameters.get("detailed", False)
        self._paragraph = config.parameters.get("paragraph", False)

    @property
    def name(self) -> str:
        """Human-readable identifier for this model."""
        return "easyocr"

    @property
    def is_available(self) -> bool:
        """Whether the EasyOCR package is installed and importable."""
        return importlib.util.find_spec("easyocr") is not None

    def _load_reader(self):
        if self._reader is None:
            import easyocr

            params = self._config.parameters or {}
            langs = params.get("languages", ["en", "ja"])
            model_dir = os.path.join(
                os.getenv("MODEL_DATA_DIR", "/app/model_data"), "easyocr"
            )
            os.makedirs(model_dir, exist_ok=True)
            self._reader = easyocr.Reader(
                langs,
                gpu=params.get("gpu", False),
                model_storage_directory=params.get("model_storage_directory") or model_dir,
            )
        return self._reader

    def warmup(self) -> None:
        self._load_reader()

    def run(self, image_path: str) -> OCRResult:
        """Run EasyOCR on the given image.

        Args:
            image_path: Path to the image file.

        Returns:
            :class:`~ocr_manga_title.schemas.OCRResult` with extracted text and
            averaged confidence.  On errors, returns a result with
            ``confidence=0.0`` and the error message.

        Raises:
            ModelNotAvailableError: If EasyOCR is not installed.

        """
        if not self.is_available:
            raise ModelNotAvailableError("EasyOCR is not installed")

        start = time.monotonic()
        try:
            reader = self._load_reader()
            results = reader.readtext(
                image_path,
                detail=1,
                paragraph=self._paragraph,
            )

            texts = [r[1] for r in results]
            confidences = [r[2] for r in results]

            raw_text = "\n".join(texts)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            elapsed_ms = int((time.monotonic() - start) * 1000)

            blocks = None
            if self._detailed:
                blocks = [
                    TextBlock(
                        bbox=[[float(p[0]), float(p[1])] for p in r[0]],
                        text=r[1],
                        confidence=float(r[2]),
                    )
                    for r in results
                    if float(r[2]) > 0
                ]

            return OCRResult(
                raw_text=raw_text,
                model_name=self.name,
                confidence=round(avg_conf, 4),
                processing_time_ms=elapsed_ms,
                blocks=blocks,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning("EasyOCR error for %s: %s", image_path, e)
            return self._make_error_result(str(e), elapsed_ms)
