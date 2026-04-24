# US-O7: Enable and Disable OCR Models

**Phase**: 0 (OCR Engine) — Sub-phase 0D  
**Priority**: Medium  
**Status**: Planned

---

## Story

> As an operator, I want to enable or disable individual OCR models via `ocrs.yaml` so that I control which models run in the pipeline without code changes.

---

## Scope

### In Scope
- `OCREngine` reads `ocrs.yaml` and instantiates only enabled + available models
- Stubs (`paddle`, `easyocr`, `glm_ocr`) always report unavailable
- Logging of model status at engine initialization
- Model registry: mapping of model name -> model class

### Out of Scope
- Dynamic model enabling/disabling without restart (Phase 1 via API)
- Model health checks (Phase 1)
- Model warm-up/preloading
- GPU/CUDA configuration per model

---

## Preconditions

1. **US-O2 complete**: `load_ocr_config()` returns `dict[str, ModelConfig]`
2. **US-O3 complete**: `MangaOCRModel` implemented
3. **US-O4 complete**: `TesseractModel` implemented
4. Stub models exist: `paddle_model.py`, `easyocr_model.py`, `glm_ocr_model.py`
5. `ocrs.yaml` has `enabled` flag for each model

---

## Implementation Details

### File: `manga_ocr/models/__init__.py`

Create a model registry that maps model names to their classes:

```python
from manga_ocr.models.base import BaseOCRModel
from manga_ocr.models.manga_ocr_model import MangaOCRModel
from manga_ocr.models.tesseract_model import TesseractModel
from manga_ocr.models.paddle_model import PaddleModel
from manga_ocr.models.easyocr_model import EasyOCRModel
from manga_ocr.models.glm_ocr_model import GLMOCRModel

MODEL_REGISTRY: dict[str, type[BaseOCRModel]] = {
    "manga_ocr": MangaOCRModel,
    "tesseract": TesseractModel,
    "paddle": PaddleModel,
    "easyocr": EasyOCRModel,
    "glm_ocr": GLMOCRModel,
}
```

### File: `manga_ocr/engine.py`

The `OCREngine.__init__()` must:

1. Iterate over `ocr_config` dict (from `load_ocr_config()`)
2. For each model config:
   - Check `config.enabled` — if `False`, log: `"Model '{name}' is disabled, skipping"` and skip
   - Look up model class in `MODEL_REGISTRY` — if not found, log warning and skip
   - Instantiate model: `model_cls(config)`
   - Check `model.is_available` — if `False`, log: `"Model '{name}' is not available, skipping"` and skip
   - Add to `self._models` list
3. Log summary: `"Initialized {n} models: {model_names}. Skipped: {skipped_names}"`
4. If no models available after initialization, log warning: `"No OCR models available. Pipeline will produce empty results."`

### Stub Model Files

Each stub (`paddle_model.py`, `easyocr_model.py`, `glm_ocr_model.py`):

```python
from manga_ocr.models.base import BaseOCRModel
from manga_ocr.schemas import OCRResult


class PaddleModel(BaseOCRModel):
    @property
    def name(self) -> str:
        return "paddle"

    @property
    def is_available(self) -> bool:
        return False

    def run(self, image_path: str) -> OCRResult:
        raise NotImplementedError(f"{self.name} integration not yet implemented")
```

Same pattern for `EasyOCRModel` (name="easyocr") and `GLMOCRModel` (name="glm_ocr").

---

## Postconditions

1. `OCREngine` only runs models that are both `enabled=true` in yaml AND `is_available=True`
2. Disabled models are logged and skipped
3. Unavailable models (stubs) are logged and skipped even if enabled
4. Engine initialization logs a clear summary of active models
5. No runtime errors from disabled/unavailable models

---

## Validation Checklist

- [ ] With `manga_ocr: enabled: true` and `tesseract: enabled: true`, both models run
- [ ] With `manga_ocr: enabled: false`, only Tesseract runs
- [ ] With `tesseract: enabled: false`, only manga-ocr runs
- [ ] With both disabled, engine has 0 models and logs warning
- [ ] With `paddle: enabled: true`, paddle is skipped because `is_available=False`
- [ ] Same for `easyocr: enabled: true` — skipped
- [ ] Same for `glm_ocr: enabled: true` — skipped
- [ ] Engine initialization logs which models are active
- [ ] Engine initialization logs which models are skipped and why
- [ ] Unknown model name in yaml (typo) is logged as warning and skipped

---

## Test Plan

### File: `tests/test_engine.py` (model selection tests)

1. `test_engine_initializes_enabled_available_models` — config with both enabled, mock both as available, assert 2 models initialized
2. `test_engine_skips_disabled_models` — manga-ocr disabled, assert only Tesseract initialized
3. `test_engine_skips_unavailable_models` — mock manga-ocr `is_available=False`, assert skipped
4. `test_engine_skips_unavailable_stubs` — enable paddle in config, assert PaddleModel skipped (is_available=False)
5. `test_engine_logs_skipped_models` — disable a model, assert log message contains model name and "disabled" or "not available"
6. `test_engine_no_models_available_logs_warning` — all disabled, assert warning about no models
7. `test_engine_unknown_model_name_warning` — add unknown model to yaml, assert warning logged
8. `test_engine_all_stubs_skipped` — enable only stub models, assert 0 active models

---

## Questions for Operator

None.

---

## Dependencies

- **US-O2** (config loading)
- **US-O3** (MangaOCRModel)
- **US-O4** (TesseractModel)
- Stub model files must exist

---

## Estimated Complexity

**Low** — straightforward registry pattern with filtering logic.
