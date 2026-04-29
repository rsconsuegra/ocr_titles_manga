"""Adapter wrapping PaddleOCR for multilingual text detection and recognition."""

import importlib.util
import logging
import threading
import time

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult, TextBlock

logger = logging.getLogger(__name__)

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

    def __init__(self, config: ModelConfig):
        self._config = config
        self._ocr = None
        self._detailed = config.parameters.get("detailed", False)

    @property
    def name(self) -> str:
        """Human-readable identifier for this model."""
        return "paddle"

    @property
    def is_available(self) -> bool:
        """Whether the PaddleOCR package is installed and importable."""
        return importlib.util.find_spec("paddleocr") is not None

    def _load_model(self):
        if self._ocr is not None:
            return self._ocr
        with _init_lock:
            if self._ocr is not None:
                return self._ocr
            from paddleocr import PaddleOCR

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
                    logger.warning("GPU init failed, falling back to CPU")
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
        self._load_model()

    def run(self, image_path: str) -> OCRResult:
        """Run PaddleOCR on the given image.

        Args:
            image_path: Path to the image file.

        Returns:
            :class:`~ocr_manga_title.schemas.OCRResult` with extracted text and
            averaged confidence.  On errors, returns a result with
            ``confidence=0.0`` and the error message.

        Raises:
            ModelNotAvailableError: If PaddleOCR is not installed.

        """
        if not self.is_available:
            raise ModelNotAvailableError("PaddleOCR is not installed")

        start = time.monotonic()
        try:
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
            elapsed_ms = int((time.monotonic() - start) * 1000)

            return OCRResult(
                raw_text=raw_text,
                model_name=self.name,
                confidence=round(avg_conf, 4),
                processing_time_ms=elapsed_ms,
                blocks=blocks if self._detailed else None,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning("PaddleOCR error for %s: %s", image_path, e)
            return self._make_error_result(str(e), elapsed_ms)
