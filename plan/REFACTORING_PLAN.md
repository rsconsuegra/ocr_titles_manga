# Architecture Refactoring Plan

## Objective

Reduce coupling, eliminate duplication, and establish patterns that make adding new features
(requirements: a new OCR model, a new API endpoint, a new pipeline stage) a 1-2 file change
instead of the current 6-7 file change.

## Table of Contents

1. [Phase 1: Unify Model Registry](#phase-1-unify-model-registry)
2. [Phase 2: Introduce Service Layer](#phase-2-introduce-service-layer)
3. [Phase 3: Global Exception Handler](#phase-3-global-exception-handler)
4. [Phase 4: Frontend Modularization](#phase-4-frontend-modularization)
5. [Phase 5: Test Infrastructure](#phase-5-test-infrastructure)
6. [Verification Checklist](#verification-checklist)

---

## Phase 1: Unify Model Registry

### Problem

Adding a new OCR model currently requires editing **7 files**:

| # | File | What to add |
|---|---|---|
| 1 | `ocr_manga_title/engine/my_model.py` | Model class |
| 2 | `ocr_manga_title/engine/ocr_engine.py:27-32` | Entry in `MODEL_REGISTRY` (name→class) |
| 3 | `ocr_manga_title/engine/__init__.py:10-14` | Duplicate entry in another `MODEL_REGISTRY` |
| 4 | `ocr_manga_title/engine/registry.py:21-99` | `ModelDescriptor` with params |
| 5 | `ocr_manga_title/api/routes/models.py:15` | Add to `VALID_MODEL_NAMES` set |
| 6 | `ocr_manga_title/config.py:20` | Add to `KNOWN_MODELS` set |
| 7 | Seed migration | DB row in `model_configs` |

### Target State

Adding a new model should require editing **2 files**: the model file itself and a single registry.

### Step 1.1: Merge the three registries into `engine/registry.py`

**File: `ocr_manga_title/engine/registry.py`**

Add `model_cls: type[BaseOCRModel]` to `ModelDescriptor`, so each descriptor carries both
the static metadata (params, label, description) AND the class reference.

```python
# Before:
@dataclass(frozen=True)
class ModelDescriptor:
    name: str
    label: str
    description: str
    params: list[ParamDescriptor] = field(default_factory=list)

# After:
@dataclass(frozen=True)
class ModelDescriptor:
    name: str
    label: str
    description: str
    model_cls: type[BaseOCRModel]    # <-- NEW: class reference
    params: list[ParamDescriptor] = field(default_factory=list)
```

Add a `known_model_names` property (derived from `MODEL_REGISTRY.keys()`) and a
`get_model_cls(name) -> type[BaseOCRModel] | None` helper.

Update each entry in `MODEL_REGISTRY` to include the class reference:

```python
MODEL_REGISTRY: dict[str, ModelDescriptor] = {
    "tesseract": ModelDescriptor(
        name="tesseract",
        label="Tesseract",
        description="Open-source OCR engine via pytesseract...",
        model_cls=TesseractModel,    # <-- NEW
        params=[...],
    ),
    ...
}
```

This requires adding imports for all model classes at the top of `registry.py`:

```python
from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.engine.tesseract_model import TesseractModel
from ocr_manga_title.engine.paddle_model import PaddleModel
from ocr_manga_title.engine.easyocr_model import EasyOCRModel
from ocr_manga_title.engine.glm_ocr_model import GLMOCRModel
```

**No circular import risk**: `registry.py` imports from concrete model files, which import
from `base.py` (which imports only `schemas`). No model file imports from `registry.py`.

### Step 1.2: Remove `MODEL_REGISTRY` from `engine/ocr_engine.py`

**File: `ocr_manga_title/engine/ocr_engine.py`**

Remove lines 27-32 (the local `MODEL_REGISTRY` dict). Change `_initialize_models()` to use
the unified registry:

```python
# Before (line 89):
model_cls = MODEL_REGISTRY.get(name)

# After:
from ocr_manga_title.engine.registry import MODEL_REGISTRY
# ... (import at top of file)
descriptor = MODEL_REGISTRY.get(name)
model_cls = descriptor.model_cls if descriptor else None
```

Also remove the individual model imports (lines 11-14) since the class references now come
from the registry.

### Step 1.3: Remove `MODEL_REGISTRY` from `engine/__init__.py`

**File: `ocr_manga_title/engine/__init__.py`**

Remove lines 10-14 (the duplicate `MODEL_REGISTRY`). The `__init__.py` should only
re-export the public API:

```python
from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.engine.ocr_engine import OCREngine as OCREngine
from ocr_manga_title.engine.registry import MODEL_REGISTRY as MODEL_REGISTRY
```

Individual model classes don't need to be re-exported — consumers who need them should
access `MODEL_REGISTRY["tesseract"].model_cls`.

### Step 1.4: Remove `VALID_MODEL_NAMES` from `api/routes/models.py`

**File: `ocr_manga_title/api/routes/models.py`**

Replace the hardcoded set (line 15):

```python
# Before:
VALID_MODEL_NAMES = {"tesseract", "paddle", "easyocr", "glm_ocr"}

# After:
from ocr_manga_title.engine.registry import MODEL_REGISTRY
VALID_MODEL_NAMES = set(MODEL_REGISTRY.keys())
```

This makes the name set automatically derived from the registry.

### Step 1.5: Remove `KNOWN_MODELS` from `config.py`

**File: `ocr_manga_title/config.py`**

Replace the hardcoded set (line 20):

```python
# Before:
KNOWN_MODELS = {"tesseract", "paddle", "easyocr", "glm_ocr"}

# After:
from ocr_manga_title.engine.registry import MODEL_REGISTRY
KNOWN_MODELS = set(MODEL_REGISTRY.keys())
```

### Step 1.6: Update `api/routes/ocr.py` to use unified registry

**File: `ocr_manga_title/api/routes/ocr.py`**

Currently imports two registries (lines 25-26):

```python
from ocr_manga_title.engine.registry import MODEL_REGISTRY, get_model
from ocr_manga_title.engine.ocr_engine import MODEL_REGISTRY as ENGINE_REGISTRY
```

After unification, only one import is needed:

```python
from ocr_manga_title.engine.registry import MODEL_REGISTRY, get_model
```

Replace all `ENGINE_REGISTRY.get(name)` calls with `descriptor.model_cls` (via `get_model()`)
or `MODEL_REGISTRY[name].model_cls`.

### Step 1.7: Update `api/routes/run.py` to use unified registry

**File: `ocr_manga_title/api/routes/run.py`**

Same pattern as Step 1.6. Remove the `ENGINE_REGISTRY` import (line 19). Use
`descriptor.model_cls` from `MODEL_REGISTRY` instead.

### Step 1.8: Verify

- Run `pytest` — all 286 tests must pass
- Run `ruff check ocr_manga_title` — no new errors
- Verify no module still references the old `engine/ocr_engine.py:MODEL_REGISTRY` or
  `engine/__init__.py:MODEL_REGISTRY`

### Result

After Phase 1, adding a new OCR model requires:

1. Create `engine/my_model.py` with the model class
2. Add one entry to `MODEL_REGISTRY` in `engine/registry.py`
3. Add a seed migration row (optional, only if it should be in the DB by default)

**3 files instead of 7.**

---

## Phase 2: Introduce Service Layer

### Problem

Business logic lives directly in route handlers (`run.py`, `ocr.py`, `results.py`) and the
worker (`ocr_worker.py`). This causes:

1. **Duplication**: `_decode_and_save()` is copy-pasted between `run.py` and `ocr.py`
2. **No reuse**: The worker can't reuse route logic, and vice versa
3. **Hard to test**: Testing business logic requires HTTP setup or Dramatiq mocking
4. **God endpoints**: `run.py:quick_run()` is 58 lines of inline orchestration

### Target Architecture

```
api/routes/*.py   →   services/*.py   →   engine/ + db/crud.py + config.py
worker/ocr_worker →   services/*.py   →   engine/ + db/crud.py + config.py
```

Routes become thin wrappers: parse request → call service → format response.
Services contain all business logic and are independently testable.

### Step 2.1: Create service package

**New file: `ocr_manga_title/services/__init__.py`** (empty)

### Step 2.2: Create `services/image.py` — image decode/encode utilities

**New file: `ocr_manga_title/services/image.py`**

Extract these functions from `api/routes/preprocess.py` and `api/routes/run.py`:

```python
"""Image encoding/decoding utilities shared across routes and services."""

import base64
import tempfile
from io import BytesIO

import cv2
import numpy as np
from PIL import Image


def decode_image(data_url: str) -> np.ndarray:
    """Decode a base64 data-URL into an OpenCV BGR numpy array."""
    # Move from preprocess.py:26-32


def encode_image(image: np.ndarray) -> str:
    """Encode an OpenCV BGR numpy array into a base64 PNG data-URL."""
    # Move from preprocess.py:35-45


def decode_and_save(data_url: str) -> str:
    """Decode a base64 data-URL and save to a temp file. Returns the file path."""
    # Move from run.py:26-35 / ocr.py:31-40 (deduplicated)


def numpy_to_temp_file(image: np.ndarray) -> str:
    """Save a numpy array as a temp PNG file. Returns the file path."""
    # Extract from run.py:52-61 (the cleanup in _run_preprocessing)
```

### Step 2.3: Create `services/preprocess.py` — preprocessing execution service

**New file: `ocr_manga_title/services/preprocess.py`**

Extract the preprocessing execution logic that's currently scattered across `preprocess.py`
(route) and `run.py`:

```python
"""Preprocessing execution service — shared by routes and worker."""

from ocr_manga_title.preprocess.registry import STEP_ORDER, STEP_REGISTRY
from ocr_manga_title.services.image import decode_image, numpy_to_temp_file


def get_step_instance(step_name: str):
    """Instantiate a preprocessing step by name."""
    # Move from preprocess.py:48-66


def run_preprocessing_pipeline(
    image_data_url: str,
    steps_config: dict,
) -> str:
    """Run preprocessing on a data URL. Returns path to processed image."""
    # Move from run.py:38-62 (_run_preprocessing)


def run_single_step(
    image_data_url: str,
    step_name: str,
    params: dict,
) -> tuple[np.ndarray, dict, int]:
    """Run a single preprocessing step. Returns (image, metadata, elapsed_ms)."""
    # Extract from preprocess.py:preview_step (lines 87-113)
```

### Step 2.4: Create `services/ocr.py` — OCR model execution service

**New file: `ocr_manga_title/services/ocr.py`**

Extract the model instantiation and execution logic that's duplicated between `run.py`
and `ocr.py`:

```python
"""OCR model execution service — shared by playground, quick run, and worker."""

from ocr_manga_title.api.schemas.ocr import OCRResultData, LLMResultData
from ocr_manga_title.engine.registry import MODEL_REGISTRY, get_model
from ocr_manga_title.schemas import ModelConfig


def build_model_config(
    model_name: str,
    overrides: dict,
) -> tuple[ModelConfig, type[BaseOCRModel] | None]:
    """Merge registry defaults with user overrides into a ModelConfig.

    Returns (config, model_cls) or (config, None) if model unknown.
    """
    # Extract the param-merging + languages normalization pattern from:
    #   run.py:81-94 and ocr.py:105-118


def run_single_model(
    model_name: str,
    image_path: str,
    overrides: dict = {},
) -> OCRResultData:
    """Instantiate and run a single OCR model.

    Returns OCRResultData with results or error.
    """
    # Extract from ocr.py:96-143


def run_all_enabled_models(
    image_path: str,
    ocr_config: dict,
) -> list[OCRResultData]:
    """Run all enabled OCR models on an image.

    Returns list of OCRResultData.
    """
    # Move from run.py:65-123 (_run_ocr_models)


def run_llm_extraction(raw_text: str) -> LLMResultData:
    """Run LLM extraction on raw OCR text.

    Returns LLMResultData (or failure placeholder).
    """
    # Move from ocr.py:163-181 (_run_llm) and the duplicate in run.py:160-175


def check_model_availability(model_name: str) -> bool:
    """Check if a model's runtime dependencies are installed."""
    # Extract from ocr.py:53-72 (the availability check in list_ocr_models)
```

### Step 2.5: Create `services/pipeline.py` — pipeline result persistence service

**New file: `ocr_manga_title/services/pipeline.py`**

Extract the result-persistence logic from `ocr_worker.py` (lines 129-177):

```python
"""Pipeline result persistence — shared by worker and future direct-run endpoints."""

from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.db.models import (
    CatalogEntry,
    OCRResult as OCRResultDB,
    PostProcessingResult,
)
from ocr_manga_title.schemas import PipelineResult


async def save_pipeline_results(
    session: AsyncSession,
    run_id,
    pipeline_result: PipelineResult,
) -> None:
    """Persist OCR results, post-processing results, and catalog entry.

    Handles:
    - Creating OCRResultDB rows for each model result
    - Creating PostProcessingResult for the best extraction
    - Creating CatalogEntry if confidence > 0.0
    """
    # Move from ocr_worker.py:129-177
```

### Step 2.6: Refactor `api/routes/run.py`

**File: `ocr_manga_title/api/routes/run.py`**

Replace the 185-line god endpoint with thin service calls:

```python
"""Quick run API route — stateless full pipeline execution."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from ocr_manga_title.api.schemas.ocr import QuickRunRequest, QuickRunResponse
from ocr_manga_title.services.image import decode_and_save
from ocr_manga_title.services.ocr import run_all_enabled_models, run_llm_extraction
from ocr_manga_title.services.preprocess import run_preprocessing_pipeline

router = APIRouter()


@router.post("/quick", response_model=QuickRunResponse)
async def quick_run(body: QuickRunRequest):
    tmp_paths: list[str] = []
    try:
        tmp_path = _decode_and_save_or_raise(body.image)
        tmp_paths.append(tmp_path)

        ocr_image_path = tmp_path
        if body.preprocess_steps:
            pp_path = run_preprocessing_pipeline(body.image, body.preprocess_steps)
            tmp_paths.append(pp_path)
            ocr_image_path = pp_path

        import time
        start_total = time.monotonic()
        ocr_results = run_all_enabled_models(ocr_image_path, body.ocr_models)

        llm_data = None
        if body.enable_llm:
            best = next(
                (r for r in sorted(ocr_results, key=lambda r: r.confidence, reverse=True)
                 if r.raw_text.strip() and not r.error),
                None,
            )
            if best:
                llm_data = run_llm_extraction(best.raw_text)

        total_ms = int((time.monotonic() - start_total) * 1000)
        return QuickRunResponse(
            ocr_results=ocr_results,
            llm=llm_data,
            total_processing_time_ms=total_ms,
        )
    finally:
        for p in tmp_paths:
            Path(p).unlink(missing_ok=True)


def _decode_and_save_or_raise(data_url: str) -> str:
    try:
        return decode_and_save(data_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}") from e
```

**Before**: 185 lines, 4 inline helper functions
**After**: ~50 lines, delegates to services

### Step 2.7: Refactor `api/routes/ocr.py`

**File: `ocr_manga_title/api/routes/ocr.py`**

Replace duplicated logic with service calls:

```python
@router.post("/run", response_model=OCRRunResponse)
async def run_ocr(body: OCRRunRequest):
    descriptor = get_model(body.model_name)
    if not descriptor:
        raise HTTPException(status_code=400, detail=f"Unknown model: {body.model_name}")

    tmp_path = None
    try:
        tmp_path = _decode_and_save_or_raise(body.image)

        ocr_data = run_single_model(body.model_name, tmp_path, body.params)
        if ocr_data.error and "not available" in ocr_data.error:
            raise HTTPException(status_code=400, detail=ocr_data.error)

        llm_data = None
        if body.enable_llm and ocr_data.raw_text.strip():
            llm_data = run_llm_extraction(ocr_data.raw_text)

        return OCRRunResponse(ocr=ocr_data, llm=llm_data)
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
```

**Before**: 206 lines
**After**: ~90 lines (registry/export endpoints remain, run endpoint simplified)

### Step 2.8: Refactor `api/routes/preprocess.py`

**File: `ocr_manga_title/api/routes/preprocess.py`**

Move `_decode_image`, `_encode_image`, `_get_step_instance` to `services/image.py` and
`services/preprocess.py`. Import from services instead.

### Step 2.9: Refactor `workers/ocr_worker.py`

**File: `ocr_manga_title/workers/ocr_worker.py`**

Use the new `services/pipeline.py:save_pipeline_results()` instead of the inline 50-line
ORM block (lines 129-177):

```python
# Before (lines 129-177): ~50 lines of manual ORM manipulation
for ocr_result in pipeline_result.ocr_results:
    ocr_db = OCRResultDB(...)
    ...
if pipeline_result.extracted:
    ...
    if best_ocr:
        ...
        pp_result = PostProcessingResult(...)
        ...
    if pipeline_result.extracted.confidence > 0.0:
        catalog_entry = CatalogEntry(...)
        ...

# After:
await save_pipeline_results(session, run.id, pipeline_result)
```

### Step 2.10: Move `results.py:override_result` ORM logic to service

**File: `ocr_manga_title/services/pipeline.py`**

Add an `override_and_sync()` function:

```python
async def override_and_sync(
    session: AsyncSession,
    result_id: uuid.UUID,
    updates: dict,
) -> PostProcessingResult | None:
    """Override post-processing result fields and propagate to catalog."""
    # Move from results.py:61-95
```

### Step 2.11: Write tests for service layer

**New file: `tests/test_services/test_ocr_service.py`**

Test `build_model_config`, `run_single_model` (mocked), `run_all_enabled_models` (mocked),
`run_llm_extraction` (mocked). No HTTP needed — pure function tests.

**New file: `tests/test_services/test_preprocess_service.py`**

Test `get_step_instance`, `run_preprocessing_pipeline` (with real steps on synthetic images).

**New file: `tests/test_services/test_pipeline_service.py`**

Test `save_pipeline_results` using SQLite in-memory (reuse shared fixture from Phase 5).

### Step 2.12: Verify

- Run `pytest` — all tests pass (existing + new service tests)
- Run `ruff check ocr_manga_title`
- Verify that no route file contains inline model instantiation, LLM calls, or
  base64 decode logic

---

## Phase 3: Global Exception Handler

### Problem

Custom exceptions (`MangaOCRError`, `ConfigurationError`, `ModelNotAvailableError`, etc.)
are defined but never translated to HTTP responses. Routes catch `Exception` generically
and return `HTTPException` manually. The custom hierarchy is effectively unused in the
API layer.

### Step 3.1: Add exception handlers to `api/app.py`

**File: `ocr_manga_title/api/app.py`**

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from ocr_manga_title.exceptions import (
    ConfigurationError,
    MangaOCRError,
    ModelNotAvailableError,
)


async def manga_error_handler(request: Request, exc: MangaOCRError) -> JSONResponse:
    """Translate MangaOCRError subclasses into structured HTTP responses."""
    status = 500
    if isinstance(exc, ConfigurationError):
        status = 400
    elif isinstance(exc, ModelNotAvailableError):
        status = 503
    return JSONResponse(
        status_code=status,
        content={"detail": str(exc)},
    )


def create_app() -> FastAPI:
    app = FastAPI(...)
    app.add_exception_handler(MangaOCRError, manga_error_handler)
    # ... rest of setup
```

### Step 3.2: Raise domain exceptions in service layer

Update the service functions from Phase 2 to raise typed exceptions instead of returning
error dicts:

```python
# services/ocr.py
def run_single_model(model_name, image_path, overrides):
    descriptor = get_model(model_name)
    if not descriptor:
        raise ModelNotAvailableError(f"Unknown model: {model_name}")
    ...
```

### Step 3.3: Verify

- Test that `ModelNotAvailableError` returns 503
- Test that `ConfigurationError` returns 400
- Test that unhandled `Exception` still returns 500 (FastAPI default)

---

## Phase 4: Frontend Modularization

### Problem

- `client.ts` is 336 lines, monolithic — all API functions + all types in one file
- `QuickRun.tsx` is 390 lines with 12 state variables — monolithic component
- Types are hand-maintained, not generated from OpenAPI

### Step 4.1: Split `client.ts` into domain modules

**Create `frontend/src/api/` directory structure:**

```
frontend/src/api/
  client.ts          → keep only apiFetch<T> + API_BASE
  types.ts           → all interfaces/types
  pipeline.ts        → uploadImages, triggerPipeline, listRuns, getRunDetail, getDashboardStats
  catalog.ts         → listCatalog, updateCatalogEntry, getCatalogExportUrl
  preprocess.ts      → getPreprocessSteps, previewStep, previewPipeline, exportPipeline
  ocr.ts             → getOCRModels, runOCR, exportOCRConfig
  run.ts             → quickRun
  index.ts           → re-export everything
```

Each file imports `apiFetch` from `client.ts` and types from `types.ts`.
`index.ts` re-exports all functions and types so existing imports (`from "./api/client"`)
can be updated with a simple find-replace.

### Step 4.2: Extract custom hooks from heavy pages

**New file: `frontend/src/hooks/useQuickRun.ts`**

```typescript
export function useQuickRun() {
  // Move the 12 useState + useEffect + handler functions from QuickRun.tsx
  // Return: { image, setImage, preprocessSteps, ocrModels, ... results, loading, error }
}
```

**New file: `frontend/src/hooks/useOcrPlayground.ts`**

```typescript
export function useOcrPlayground() {
  // Move state management from OcrPlayground.tsx
}
```

**New file: `frontend/src/hooks/usePreprocessPlayground.ts`**

```typescript
export function usePreprocessPlayground() {
  // Move state management from PreprocessPlayground.tsx
}
```

### Step 4.3: Extract `ImageUploader` reuse

Currently `QuickRun.tsx`, `OcrPlayground.tsx`, and `PreprocessPlayground.tsx` each have
inline file-upload UIs. Replace with the existing `ImageUploader` component or a new
shared `ImageInput` component that handles:

- File selection → base64 data URL conversion
- Preview display
- Drag-and-drop

### Step 4.4: Verify

- `npm run build` — TypeScript clean, Vite build succeeds
- All pages work identically (visual check)
- No increase in bundle size (tree-shaking should handle the split)

---

## Phase 5: Test Infrastructure

### Problem

- `tests/test_db/conftest.py` and `tests/test_worker/conftest.py` are **identical** (22 lines each)
- `tests/test_api/conftest.py` duplicates the same `db_engine` fixture with additional setup
- No shared `db_session` fixture — each conftest defines its own

### Step 5.1: Consolidate shared fixtures into `tests/conftest.py`

**File: `tests/conftest.py`**

Add the shared DB fixtures:

```python
@pytest.fixture
async def db_engine():
    """In-memory SQLite engine with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Async DB session backed by in-memory SQLite."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
```

### Step 5.2: Remove duplicate fixtures from sub-conftests

**File: `tests/test_db/conftest.py`** — delete `db_engine` and `db_session` (use root)
**File: `tests/test_worker/conftest.py`** — delete `db_engine` and `db_session` (use root)

**File: `tests/test_api/conftest.py`** — keep only the `client` fixture (which needs
special monkeypatch setup). Remove `db_engine` (use root).

### Step 5.3: Verify

- Run `pytest` — all 286+ tests pass
- Confirm fixtures resolve from root conftest correctly

---

## Verification Checklist

After all phases are complete:

```bash
# 1. All tests pass
make test

# 2. No lint errors
make lint

# 3. Frontend builds clean
cd frontend && npm run build

# 4. No dead imports (manual check)
#    - grep -r "ENGINE_REGISTRY" ocr_manga_title/  → 0 results
#    - grep -r "VALID_MODEL_NAMES" ocr_manga_title/  → only in models.py, derived from registry
#    - grep -r "KNOWN_MODELS" ocr_manga_title/  → only in config.py, derived from registry

# 5. Adding a new model touches only 2-3 files
# 6. Adding a new API endpoint can reuse service functions
# 7. Business logic is testable without HTTP/Dramatiq
```

## Risk Assessment

| Phase | Risk | Mitigation |
|---|---|---|
| 1 (Registry) | Low — mechanical refactoring | Run full test suite after each step |
| 2 (Services) | Medium — significant code moves | Do one service at a time, run tests between each |
| 3 (Exceptions) | Low — additive change | Exception handler is opt-in; existing routes still work |
| 4 (Frontend) | Low — file reorganization | No logic changes, just moving code |
| 5 (Tests) | Low — fixture consolidation | pytest fixture resolution is well-defined |

## Execution Order

Phases can be done independently. Recommended order:

1. **Phase 5** (Tests) — 30 min, reduces risk for everything else
2. **Phase 1** (Registry) — 2-3 hours, highest ROI
3. **Phase 3** (Exceptions) — 30 min, simple additive change
4. **Phase 2** (Services) — 4-6 hours, biggest architectural win
5. **Phase 4** (Frontend) — 3-4 hours, independent of backend changes
