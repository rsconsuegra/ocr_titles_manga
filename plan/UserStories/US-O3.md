# US-O3: Run manga-ocr on Japanese Text

**Phase**: 0 (OCR Engine) — Sub-phase 0B  
**Priority**: High  
**Status**: Planned

---

## Story

> As an operator, I want to use the manga-ocr model to extract Japanese text from manga panel images so that I get specialized recognition for manga-specific text (speech bubbles, overlays, stylized fonts).

---

## Scope

### In Scope
- `MangaOCRModel` class implementing `BaseOCRModel` interface
- Lazy model loading from HuggingFace (`kha-white/manga-ocr-simplified`)
- Image preprocessing (PIL Image conversion)
- `OCRResult` output with raw text, confidence, processing time
- Singleton pattern for model reuse across calls
- Graceful handling of corrupt images and missing model files

### Out of Scope
- Image preprocessing beyond PIL conversion (no resizing, contrast, rotation — Phase 4+)
- Batch processing
- GPU configuration (auto-detect, use CPU if no CUDA)
- Model fine-tuning
- Custom model weights/paths

---

## Preconditions

1. **US-O2 complete**: `schemas.py` has `OCRResult` model, `exceptions.py` has `ModelNotAvailableError`
2. **US-O2 complete**: `models/base.py` has `BaseOCRModel` abstract class
3. `pyproject.toml` has `manga-ocr` and `pillow` in dependencies
4. HuggingFace model cache directory accessible (`~/.cache/huggingface/`)
5. Internet available for first model download

---

## Implementation Details

### File: `manga_ocr/models/base.py`

Must be implemented first (or as part of this story if not yet done):

```python
from abc import ABC, abstractmethod
from manga_ocr.schemas import OCRResult


class BaseOCRModel(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def run(self, image_path: str) -> OCRResult: ...
```

### File: `manga_ocr/models/manga_ocr_model.py`

```python
class MangaOCRModel(BaseOCRModel):
    def __init__(self, config: ModelConfig): ...

    @property
    def name(self) -> str:
        return "manga-ocr"

    @property
    def is_available(self) -> bool:
        # Check if manga_ocr package is importable
        # Return True/False without raising

    def _load_model(self):
        # Lazy load: only called on first run()
        # Use manga_ocr package (pip install manga-ocr)
        # from manga_ocr import MangaOcr
        # self._model = MangaOcr()
        # Store as instance attribute for singleton reuse

    def run(self, image_path: str) -> OCRResult:
        # 1. Validate image_path exists
        # 2. Open with PIL Image
        # 3. If model not loaded, call _load_model()
        # 4. Start timer
        # 5. Call self._model(image) — returns string
        # 6. Stop timer
        # 7. Return OCRResult(
        #      raw_text=result_str,
        #      model_name="manga-ocr",
        #      confidence=0.7,  # default; manga-ocr doesn't provide confidence scores
        #      processing_time_ms=elapsed_ms
        #    )
        # 8. On error: return OCRResult with empty raw_text, confidence=0.1, error=str(e)
```

Key decisions:
- The `manga-ocr` package exposes `MangaOcr` class. Usage: `MangaOcr()(image_or_path)` returns a string.
- Confidence is set to `0.7` default because manga-ocr does not provide confidence scores. This is a placeholder.
- Lazy loading: constructor does NOT load model. First `run()` call triggers load. This avoids loading model at import time or during config validation.
- Singleton: once loaded, model is reused. Check `self._model is None` to decide if load needed.
- Error cases to handle:
  - `image_path` does not exist: raise `FileNotFoundError`
  - Image file is corrupt/unreadable: catch PIL `UnidentifiedImageError`, return `OCRResult` with error
  - `manga_ocr` import fails: `is_available` returns `False`, `run()` raises `ModelNotAvailableError`
  - Model download fails (network): catch and return `OCRResult` with error

---

## Postconditions

1. `MangaOCRModel` can be instantiated with a `ModelConfig`
2. `is_available` returns `True` when `manga-ocr` package is installed
3. `run()` loads model on first call, reuses on subsequent calls
4. `run()` returns `OCRResult` with Japanese text from manga panel images
5. `run()` returns gracefully (no unhandled exception) on corrupt images
6. Model is loaded exactly once per `MangaOCRModel` instance

---

## Validation Checklist

- [ ] `MangaOCRModel(config).name == "manga-ocr"`
- [ ] `MangaOCRModel(config).is_available` returns bool (True if package installed)
- [ ] First call to `run()` loads model (measurable delay)
- [ ] Second call to `run()` does NOT reload model (no delay)
- [ ] `run("valid_manga_panel.png")` returns `OCRResult` with non-empty `raw_text` containing Japanese characters
- [ ] `run("nonexistent.png")` raises `FileNotFoundError`
- [ ] `run("corrupt.png")` returns `OCRResult` with error message
- [ ] `run("blank_image.png")` returns `OCRResult` with empty or minimal `raw_text`, low confidence

---

## Test Plan

### File: `tests/test_models.py` (section for manga-ocr)

**Mocked tests** (no real model weights needed):

1. `test_manga_ocr_name` — assert `model.name == "manga-ocr"`
2. `test_manga_ocr_is_available_when_installed` — mock import, assert `True`
3. `test_manga_ocr_is_available_when_not_installed` — mock import to raise ImportError, assert `False`
4. `test_manga_ocr_run_returns_ocr_result` — mock `MangaOcr()` to return "テスト", assert `OCRResult` structure
5. `test_manga_ocr_run_lazy_loads_model` — mock `MangaOcr`, verify constructor NOT called until `run()`
6. `test_manga_ocr_run_reuses_model` — call `run()` twice, verify `MangaOcr()` instantiated once
7. `test_manga_ocr_run_records_processing_time` — assert `processing_time_ms >= 0`
8. `test_manga_ocr_run_nonexistent_image_raises` — assert `FileNotFoundError` for bad path
9. `test_manga_ocr_run_corrupt_image_returns_error` — mock PIL to raise `UnidentifiedImageError`, assert `OCRResult.error` is set
10. `test_manga_ocr_default_confidence` — assert confidence is `0.7` when model returns text

**Test fixture**: Create a minimal test image using PIL (1x1 white pixel PNG) for tests that need a real file but not a real manga image.

```python
@pytest.fixture
def blank_image(tmp_path):
    img = Image.new("RGB", (1, 1), "white")
    path = tmp_path / "blank.png"
    img.save(path)
    return str(path)
```

---

## Questions for Operator

None.

---

## Dependencies

- **US-O2** (config, schemas, exceptions, base interface) must be complete
- `pyproject.toml` must have `manga-ocr` and `pillow` in dependencies

---

## Estimated Complexity

**Medium** — wrapper is simple, but lazy loading, error handling, and testing with mocks add moderate complexity.
