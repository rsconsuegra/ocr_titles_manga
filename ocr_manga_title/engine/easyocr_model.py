"""Adapter wrapping EasyOCR for multilingual text detection and recognition."""

import os
from typing import Any

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult, TextBlock


class EasyOCRModel(BaseOCRModel):
    """OCR adapter for EasyOCR with lazy reader loading and configurable languages."""

    def __init__(self, config: ModelConfig) -> None:
        """Initialize the EasyOCR adapter.

        Args:
            config: Model configuration including language list and paragraph mode.

        """
        super().__init__(config)
        self._reader = None
        self._paragraph = config.parameters.get("paragraph", False)

    @property
    def name(self) -> str:
        """Machine-readable identifier for this model."""
        return "easyocr"

    @property
    def is_available(self) -> bool:
        """Whether this model's runtime dependencies are installed."""
        return self._is_package_installed("easyocr")

    def _load_reader(self) -> Any:
        if self._reader is None:
            import easyocr  # type: ignore[import-not-found]

            params = self._config.parameters or {}
            langs = params.get("languages", ["en", "ja"])
            model_dir = os.path.join(
                os.getenv("MODEL_DATA_DIR", "/app/model_data"), "easyocr"
            )
            os.makedirs(model_dir, exist_ok=True)
            self._reader = easyocr.Reader(
                langs,
                gpu=params.get("gpu", False),
                model_storage_directory=params.get("model_storage_directory")
                or model_dir,
            )
        return self._reader

    def warmup(self) -> None:
        """Pre-load the EasyOCR model into memory."""
        self._load_reader()

    def _do_run(self, image_path: str) -> OCRResult:
        """Execute OCR and return raw results."""
        if not self.is_available:
            raise ModelNotAvailableError("EasyOCR is not installed")

        reader = self._load_reader()
        results = reader.readtext(
            image_path,
            detail=1,
            paragraph=self._paragraph,
        )

        texts = []
        confidences = []
        for r in results:
            texts.append(r[1])
            confidences.append(float(r[2]) if len(r) > 2 else 0.0)

        raw_text = "\n".join(texts)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        blocks = None
        if self._detailed:
            blocks = [
                TextBlock(
                    bbox=[[float(p[0]), float(p[1])] for p in r[0]],
                    text=r[1],
                    confidence=float(r[2]) if len(r) > 2 else 0.0,
                )
                for r in results
                if (float(r[2]) if len(r) > 2 else 0.0) > 0
            ]

        return OCRResult(
            raw_text=raw_text,
            model_name=self.name,
            confidence=round(avg_conf, 4),
            processing_time_ms=0,
            blocks=blocks,
        )
