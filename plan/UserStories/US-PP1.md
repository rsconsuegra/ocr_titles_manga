# US-PP1: Browse Available Preprocessing Steps

**Feature**: Preprocessing Playground
**Depends on**: Phase 1 complete (preprocessing steps exist)
**Blocks**: US-PP2 (single preview), US-PP3 (pipeline preview), US-PP5 (parameter forms)

---

## Overview

Create a step descriptor registry and an API endpoint that returns all available preprocessing steps with their configurable parameter schemas. This is the foundation for the playground — the frontend uses the step catalog to render the interactive UI.

---

## Implementation Details

### 1. `ocr_manga_title/preprocess/registry.py` (new)

Hard-coded step descriptor registry. Each entry contains:

- `display_name`: Human-readable step name
- `description`: What the step does
- `category`: Grouping tag (transform, color, enhance, threshold)
- `params`: Dict of parameter name → descriptor with `type`, `default`, `options`, `min`, `max`, `step`

Five entries following `STEP_ORDER = ["roi", "grayscale", "upscale", "denoise", "binarize"]`.

Also exposes `get_step_descriptors() -> list[dict]`:
1. Iterates `STEP_ORDER`
2. Instantiates each step class to check `is_available`
3. Returns descriptor with `is_available` flag

### 2. `ocr_manga_title/api/schemas/preprocess.py` (new)

Pydantic models:
- `StepParamDescriptor`: type, default, options, min, max, step
- `StepDescriptor`: name, display_name, description, category, is_available, params

### 3. `ocr_manga_title/api/routes/preprocess.py` (new)

```python
@router.get("/steps", response_model=list[StepDescriptor])
async def list_steps():
    return get_step_descriptors()
```

### 4. `ocr_manga_title/api/app.py` (modified)

Register preprocess router:
```python
from ocr_manga_title.api.routes import preprocess
app.include_router(preprocess.router, prefix="/api/v1/preprocess", tags=["preprocess"])
```

### 5. `ocr_manga_title/api/schemas/__init__.py` (modified)

Export new schema classes.

---

## Acceptance Criteria

- [ ] `GET /api/v1/preprocess/steps` returns 5 step descriptors in canonical order
- [ ] Each descriptor has: name, display_name, description, category, is_available, params
- [ ] Parameter descriptors include type, default, and constraints
- [ ] ROI descriptor has 4 params: method (select), min_area (int), padding (int), merge_overlap (float)
- [ ] Grayscale descriptor has 0 params
- [ ] Upscale descriptor has 2 params: method (select), scale_factor (select)
- [ ] Denoise descriptor has 2 params: method (select), strength (select)
- [ ] Binarize descriptor has 4 params: method (select), invert (bool), block_size (int), c (int)
- [ ] Unknown step name is not returned (only known steps)
- [ ] Router registered in app factory at `/api/v1/preprocess`

---

## Test Specifications

**File**: `tests/test_api/test_preprocess.py`

Tests:
- `test_list_steps_returns_5_steps`: GET /steps returns exactly 5 items
- `test_steps_in_canonical_order`: Names are ["roi", "grayscale", "upscale", "denoise", "binarize"]
- `test_step_has_required_fields`: Each step has name, display_name, description, category, is_available, params
- `test_grayscale_has_no_params`: grayscale step params is empty dict
- `test_binarize_has_4_params`: binarize step has method, invert, block_size, c
- `test_select_param_has_options`: method param in binarize has options list
- `test_int_param_has_range`: block_size in binarize has min, max, step
