"""Adapter wrapping PaddleOCR for multilingual text detection and recognition."""

import threading
from typing import Any

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult, TextBlock

_LANG_MAP = {
    "en": "en",
    "ja": "japan",
    "jpn": "japan",
    "ch": "ch",
    "chi_sim": "ch",
    "ko": "korean",
    "kor": "korean",
    "spa": "latin",
    "fra": "french",
    "deu": "german",
    "por": "latin",
    "ita": "latin",
}

_init_lock = threading.Lock()


class PaddleModel(BaseOCRModel):
    """OCR adapter for PaddleOCR with lazy model loading and configurable languages."""

    def __init__(self, config: ModelConfig) -> None:
        """Initialize the PaddleOCR adapter.

        Args:
            config: Model configuration including language and GPU settings.

        """
        super().__init__(config)
        self._ocr = None

    @property
    def name(self) -> str:
        """Machine-readable identifier for this model."""
        return "paddle"

    @property
    def is_available(self) -> bool:
        """Whether this model's runtime dependencies are installed."""
        return self._is_package_installed("paddleocr")

    def _load_model(self) -> Any:
        if self._ocr is not None:
            return self._ocr
        with _init_lock:
            if self._ocr is not None:
                return self._ocr
            from paddleocr import PaddleOCR  # type: ignore[import-not-found]

            params = self._config.parameters or {}
            lang = params.get("languages", ["en", "ja"])
            if isinstance(lang, list):
                paddle_lang = _LANG_MAP.get(lang[0], lang[0])
            else:
                paddle_lang = _LANG_MAP.get(lang, lang)

            use_gpu = params.get("use_gpu", False)
            try:
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=paddle_lang,
                    use_gpu=use_gpu,
                    show_log=False,
                )
            except RuntimeError:
                if use_gpu:
                    self._logger.warning("GPU init failed, falling back to CPU")
                    self._ocr = PaddleOCR(
                        use_angle_cls=True,
                        lang=paddle_lang,
                        use_gpu=False,
                        show_log=False,
                    )
                else:
                    raise
            return self._ocr

    def warmup(self) -> None:
        """Pre-load the PaddleOCR model into memory."""
        self._load_model()

    def _do_run(self, image_path: str) -> OCRResult:
        """Execute OCR and return raw results."""
        if not self.is_available:
            raise ModelNotAvailableError("PaddleOCR is not installed")

        ocr = self._load_model()
        result = ocr.ocr(image_path, cls=True)

        texts = []
        confidences = []
        blocks = []
        for page in result or []:
            for line in page or []:
                if line and len(line) >= 2:
                    texts.append(line[1][0])
                    confidences.append(line[1][1])
                    if self._detailed:
                        blocks.append(
                            TextBlock(
                                bbox=[[float(p[0]), float(p[1])] for p in line[0]],
                                text=line[1][0],
                                confidence=float(line[1][1]),
                            )
                        )

        raw_text = "\n".join(texts)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(
            raw_text=raw_text,
            model_name=self.name,
            confidence=round(avg_conf, 4),
            processing_time_ms=0,
            blocks=blocks if self._detailed else None,
        )
