# US-2A1: Run PaddleOCR for Manga Text Extraction

**Sub-phase**: 2A — Additional OCR Models
**Depends on**: Step 1 (Update Dependencies — `paddleocr` dep), US-1A2 (ModelConfig table)
**Blocks**: US-2C1 (pipeline diagram shows enabled models)

---

## Overview

Replace the PaddleOCR stub in `ocr_manga_title/engine/paddle_model.py` with a working adapter that lazy-loads the `paddleocr` Python package, runs OCR on manga images, and returns structured `OCRResult` data. The adapter must support configurable languages, GPU toggle, and gracefully handle missing packages and corrupt images.

---

## Implementation Details

### 1. `ocr_manga_title/engine/paddle_model.py`

Replace the existing stub with a full PaddleOCR wrapper:

```python
import importlib.util
import time
import logging

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.schemas import ModelConfig, OCRResult
from ocr_manga_title.exceptions import ModelNotAvailableError

logger = logging.getLogger(__name__)


class PaddleModel(BaseOCRModel):
    def __init__(self, config: ModelConfig):
        self._config = config
        self._ocr = None

    @property
    def name(self) -> str:
        return "paddle"

    @property
    def is_available(self) -> bool:
        return importlib.util.find_spec("paddleocr") is not None

    def _load_model(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR

            params = self._config.parameters or {}
            lang = params.get("languages", ["en", "ja"])
            lang_map = {"en": "en", "ja": "japan", "jpn": "japan"}
            paddle_lang = (
                lang_map.get(lang[0], lang[0]) if isinstance(lang, list) else lang
            )
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=paddle_lang,
                use_gpu=params.get("use_gpu", False),
                show_log=False,
            )
        return self._ocr

    def run(self, image_path: str) -> OCRResult:
        if not self.is_available:
            raise ModelNotAvailableError("PaddleOCR is not installed")

        start = time.monotonic()
        try:
            ocr = self._load_model()
            result = ocr.ocr(image_path, cls=True)

            texts = []
            confidences = []
            for page in result or []:
                for line in page or []:
                    if line and len(line) >= 2:
                        texts.append(line[1][0])
                        confidences.append(line[1][1])

            raw_text = "\n".join(texts)
            avg_conf = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)

            return OCRResult(
                raw_text=raw_text,
                model_name=self.name,
                confidence=round(avg_conf, 4),
                processing_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning("PaddleOCR error for %s: %s", image_path, e)
            return OCRResult(
                raw_text="",
                model_name=self.name,
                confidence=0.0,
                processing_time_ms=elapsed_ms,
                error=str(e),
            )
```

### 2. `ocr_manga_title/engine/registry.py` (partial update)

Update PaddleOCR's `ModelDescriptor` params:

```python
"paddle": ModelDescriptor(
    name="paddle",
    label="PaddleOCR",
    description="PaddlePaddle OCR engine with multilingual support",
    model_cls=PaddleModel,
    params=[
        ParamDescriptor(
            name="languages",
            type="multiselect",
            default=["en", "ja"],
            options=["en", "ja", "ch", "ko"],
            label="Languages",
            description="OCR languages",
        ),
        ParamDescriptor(
            name="use_gpu",
            type="boolean",
            default=False,
            label="Use GPU",
            description="Enable CUDA acceleration",
        ),
    ],
),
```

### 3. `config/ocrs.yaml` (partial update)

```yaml
  paddle:
    enabled: false
    languages: ["en", "ja"]
    use_gpu: false
```

---

## Acceptance Criteria

- [ ] PaddleOCR model listed in `GET /api/v1/models` with enabled/disabled status
- [ ] When enabled, PaddleOCR runs during pipeline execution alongside other enabled models
- [ ] `is_available` returns `True` when `paddleocr` package installed, `False` otherwise
- [ ] Model supports configurable languages (EN, JA, CH, KO) via model config parameters
- [ ] Model supports GPU acceleration toggle via model config parameters
- [ ] First `run()` call lazy-loads PaddleOCR model; subsequent calls reuse loaded model
- [ ] Returns `OCRResult` with raw text, average confidence score, and processing time
- [ ] Handles corrupt images: returns `OCRResult` with empty text, confidence 0.0, error message
- [ ] Falls back to CPU if CUDA unavailable (logs warning)

---

## Test Specifications

**File**: `tests/test_engine/test_paddle_model.py`

Tests:
- `test_is_available_returns_true_when_paddleocr_installed` — mock `importlib.util.find_spec("paddleocr")` to return truthy
- `test_is_available_returns_false_when_paddleocr_missing` — mock `find_spec` to return `None`
- `test_run_returns_ocr_result_with_text` — mock `PaddleOCR` constructor and `.ocr()` to return `[[[box, ("hello", 0.95)]]]`; verify `raw_text="hello"`, `confidence=0.95`
- `test_run_returns_empty_on_corrupt_image` — mock `.ocr()` to raise `RuntimeError`; verify `raw_text=""`, `confidence=0.0`, `error` is set
- `test_run_raises_when_not_available` — mock `is_available` to `False`; verify `ModelNotAvailableError` raised
- `test_lazy_load_creates_model_on_first_run` — call `run()` twice, verify `PaddleOCR()` constructor called once
- `test_configurable_language_and_gpu` — pass `parameters={"languages": ["ja"], "use_gpu": True}`, verify passed to `PaddleOCR()`
- `test_name_returns_paddle` — verify `name` property returns `"paddle"`
