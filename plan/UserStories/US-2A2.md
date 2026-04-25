# US-2A2: Run EasyOCR for Manga Text Extraction

**Sub-phase**: 2A — Additional OCR Models
**Depends on**: Step 1 (Update Dependencies — `easyocr` dep), US-1A2 (ModelConfig table)
**Blocks**: US-2C1 (pipeline diagram shows enabled models)

---

## Overview

Replace the EasyOCR stub in `ocr_manga_title/engine/easyocr_model.py` with a working adapter that lazy-loads the `easyocr` Python package, runs OCR on manga images, and returns structured `OCRResult` data. The adapter must support configurable languages, GPU toggle, and gracefully handle missing packages and corrupt images.

---

## Implementation Details

### 1. `ocr_manga_title/engine/easyocr_model.py`

Replace the existing stub with a full EasyOCR wrapper:

```python
import importlib.util
import time
import logging

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.schemas import ModelConfig, OCRResult
from ocr_manga_title.exceptions import ModelNotAvailableError

logger = logging.getLogger(__name__)


class EasyOCRModel(BaseOCRModel):
    def __init__(self, config: ModelConfig):
        self._config = config
        self._reader = None

    @property
    def name(self) -> str:
        return "easyocr"

    @property
    def is_available(self) -> bool:
        return importlib.util.find_spec("easyocr") is not None

    def _load_reader(self):
        if self._reader is None:
            import easyocr

            params = self._config.parameters or {}
            langs = params.get("languages", ["en", "ja"])
            self._reader = easyocr.Reader(
                langs,
                gpu=params.get("gpu", False),
                model_storage_directory=params.get("model_storage_directory"),
            )
        return self._reader

    def run(self, image_path: str) -> OCRResult:
        if not self.is_available:
            raise ModelNotAvailableError("EasyOCR is not installed")

        start = time.monotonic()
        try:
            reader = self._load_reader()
            results = reader.readtext(image_path)

            texts = [r[1] for r in results]
            confidences = [r[2] for r in results]

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
            logger.warning("EasyOCR error for %s: %s", image_path, e)
            return OCRResult(
                raw_text="",
                model_name=self.name,
                confidence=0.0,
                processing_time_ms=elapsed_ms,
                error=str(e),
            )
```

### 2. `ocr_manga_title/engine/registry.py` (partial update)

Update EasyOCR's `ModelDescriptor` params:

```python
"easyocr": ModelDescriptor(
    name="easyocr",
    label="EasyOCR",
    description="PyTorch-based OCR with multilingual support",
    model_cls=EasyOCRModel,
    params=[
        ParamDescriptor(
            name="languages",
            type="multiselect",
            default=["en", "ja"],
            options=["en", "ja", "ch_sim", "ch_tra", "ko"],
            label="Languages",
            description="OCR languages",
        ),
        ParamDescriptor(
            name="gpu",
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
  easyocr:
    enabled: false
    languages: ["en", "ja"]
    gpu: false
```

---

## Acceptance Criteria

- [ ] EasyOCR model listed in `GET /api/v1/models` with enabled/disabled status
- [ ] When enabled, EasyOCR runs during pipeline execution alongside other enabled models
- [ ] `is_available` returns `True` when `easyocr` package installed, `False` otherwise
- [ ] Model supports configurable languages (EN, JA, CH, KO) via model config parameters
- [ ] Model supports GPU toggle via model config parameters
- [ ] First `run()` call lazy-loads EasyOCR reader; subsequent calls reuse it
- [ ] Returns `OCRResult` with raw text, per-word averaged confidence, and processing time
- [ ] Handles corrupt images: returns `OCRResult` with empty text, confidence 0.0, error message

---

## Test Specifications

**File**: `tests/test_engine/test_easyocr_model.py`

Tests:
- `test_is_available_returns_true_when_easyocr_installed` — mock `find_spec("easyocr")` to return truthy
- `test_is_available_returns_false_when_easyocr_missing` — mock `find_spec` to return `None`
- `test_run_returns_ocr_result_with_text` — mock `easyocr.Reader` and `.readtext()` to return `[(bbox, "manga title", 0.92)]`; verify `raw_text="manga title"`, `confidence=0.92`
- `test_run_returns_empty_on_corrupt_image` — mock `.readtext()` to raise `RuntimeError`; verify error handling
- `test_run_raises_when_not_available` — mock `is_available` to `False`; verify `ModelNotAvailableError`
- `test_lazy_load_creates_reader_on_first_run` — call `run()` twice, verify `easyocr.Reader()` called once
- `test_reader_uses_configured_languages` — pass `parameters={"languages": ["ja", "en"], "gpu": True}`, verify passed to `Reader()`
- `test_name_returns_easyocr` — verify `name` property returns `"easyocr"`
