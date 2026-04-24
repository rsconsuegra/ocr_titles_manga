# Preprocessing Playground Plan

**Phase**: Feature (Preprocessing Playground)
**Scope**: Interactive workbench for testing image preprocessing steps, composing pipelines, and exporting configs
**Goal**: Let users visually evaluate each preprocessing transformation on their own images before committing to automated processing
**Prerequisite**: Phase 1 (MVP Backend API) — complete with 5 preprocessing steps in `ocr_manga_title/preprocess/`

---

## What We Are Building

A web-based playground where users upload a manga image, test each of the 5 preprocessing steps individually with real-time side-by-side previews, compose a multi-step pipeline (enforcing canonical order), see intermediate results after every step, and export the configuration as a `preprocess.yaml`-compatible file for reuse in the automated pipeline.

**Key design decisions**:
- **Preprocessing only** — no OCR execution in the playground. Users export config, then use the main Upload/Run pipeline for full OCR.
- **Canonical step order enforced** — `roi → grayscale → upscale → denoise → binarize`. Users toggle which steps to include but cannot reorder.
- **All intermediates shown** — pipeline preview returns an image after each step, displayed as a horizontal filmstrip.
- **Stateless server** — no session management. Each request sends the image + config. Manga panels are small enough for this to be performant.

---

## What We Are NOT Building

- No OCR preview on preprocessed images
- No free step reordering
- No persistent playground sessions or saved pipelines (stateless)
- No batch processing in the playground (single image only)
- No authentication or authorization
- No WebSocket for real-time progress

---

## Existing Infrastructure

### Preprocessing Steps (5, in canonical order)

| Step | Key | Configurable Params | Defaults |
|---|---|---|---|
| ROI | `roi` | method (`contour`), min_area, padding, merge_overlap | contour, 500, 10, 0.3 |
| Grayscale | `grayscale` | *(none)* | — |
| Upscale | `upscale` | method (`cubic`/`fsrcnn`/`edsr`), scale_factor (2/3/4) | cubic, 2 |
| Denoise | `denoise` | method (`gaussian`/`median`/`nlmeans`), strength (`light`/`medium`/`heavy`) | gaussian, light |
| Binarize | `binarize` | method (`otsu`/`adaptive_gaussian`/`adaptive_mean`), invert, block_size, c | otsu, false, 11, 2 |

### Key Files

- `ocr_manga_title/preprocess/base.py` — `BasePreProcessor` ABC with `name`, `is_available`, `process(image, config) -> (image, metadata)`
- `ocr_manga_title/preprocess/pipeline.py` — `PreProcessingPipeline` with `STEP_ORDER = ["roi", "grayscale", "upscale", "denoise", "binarize"]`
- `ocr_manga_title/preprocess/steps/` — 5 step implementations
- `config/preprocess.yaml` — current config format to match for export

---

## Target Directory Structure (additions only)

```
ocr_manga_title/
  preprocess/
    registry.py                         # NEW — step descriptor registry
  api/
    routes/
      preprocess.py                     # NEW — playground API endpoints
    schemas/
      preprocess.py                     # NEW — request/response models
frontend/src/
  api/
    client.ts                          # MODIFIED — add 4 API functions
  components/
    ImageCompare.tsx                    # NEW — side-by-side image display
    PreprocessStepCard.tsx              # NEW — step accordion with param form
    PipelineFilmstrip.tsx               # NEW — horizontal intermediate results
  pages/
    PreprocessPlayground.tsx            # NEW — main playground page
  App.tsx                              # MODIFIED — add /playground route
tests/
  test_api/
    test_preprocess.py                  # NEW — API endpoint tests
```

---

## Architecture

### Backend

#### 1. Step Registry (`ocr_manga_title/preprocess/registry.py`)

Hard-coded descriptor for each of the 5 steps. Returns ordered list following `STEP_ORDER`.

```python
STEP_REGISTRY = {
    "roi": {
        "display_name": "Region of Interest",
        "description": "Detect and crop the text-dense region of the image using contour detection",
        "category": "transform",
        "params": {
            "method": {
                "type": "select",
                "options": ["contour"],
                "default": "contour",
            },
            "min_area": {
                "type": "int",
                "min": 100,
                "max": 10000,
                "default": 500,
            },
            "padding": {
                "type": "int",
                "min": 0,
                "max": 100,
                "default": 10,
            },
            "merge_overlap": {
                "type": "float",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.3,
            },
        },
    },
    "grayscale": {
        "display_name": "Grayscale",
        "description": "Convert BGR/BGRA image to single-channel grayscale",
        "category": "color",
        "params": {},
    },
    "upscale": {
        "display_name": "Upscale",
        "description": "Increase image resolution using interpolation or DNN super-resolution",
        "category": "enhance",
        "params": {
            "method": {
                "type": "select",
                "options": ["cubic", "fsrcnn", "edsr"],
                "default": "cubic",
            },
            "scale_factor": {
                "type": "select",
                "options": [2, 3, 4],
                "default": 2,
            },
        },
    },
    "denoise": {
        "display_name": "Denoise",
        "description": "Reduce image noise using Gaussian, median, or non-local means filtering",
        "category": "enhance",
        "params": {
            "method": {
                "type": "select",
                "options": ["gaussian", "median", "nlmeans"],
                "default": "gaussian",
            },
            "strength": {
                "type": "select",
                "options": ["light", "medium", "heavy"],
                "default": "light",
            },
        },
    },
    "binarize": {
        "display_name": "Binarize",
        "description": "Convert to binary (black and white) using Otsu or adaptive thresholding",
        "category": "threshold",
        "params": {
            "method": {
                "type": "select",
                "options": ["otsu", "adaptive_gaussian", "adaptive_mean"],
                "default": "otsu",
            },
            "invert": {
                "type": "bool",
                "default": False,
            },
            "block_size": {
                "type": "int",
                "min": 3,
                "max": 99,
                "step": 2,
                "default": 11,
            },
            "c": {
                "type": "int",
                "min": 0,
                "max": 20,
                "default": 2,
            },
        },
    },
}

STEP_ORDER = ["roi", "grayscale", "upscale", "denoise", "binarize"]
```

Exposes `get_step_descriptors() -> list[dict]` which:
1. Iterates `STEP_ORDER`
2. Checks runtime availability via step class `is_available`
3. Returns the descriptor with an `is_available` flag

#### 2. API Schemas (`ocr_manga_title/api/schemas/preprocess.py`)

```python
from typing import Any
from pydantic import BaseModel


class StepParamDescriptor(BaseModel):
    type: str
    default: Any
    options: list[Any] | None = None
    min: int | float | None = None
    max: int | float | None = None
    step: int | float | None = None


class StepDescriptor(BaseModel):
    name: str
    display_name: str
    description: str
    category: str
    is_available: bool
    params: dict[str, StepParamDescriptor]


class PreviewStepRequest(BaseModel):
    step_name: str
    config: dict[str, Any]


class PreviewStepResponse(BaseModel):
    image: str
    metadata: dict[str, Any]
    processing_time_ms: int


class PipelineStepConfig(BaseModel):
    step_name: str
    enabled: bool
    config: dict[str, Any]


class StepIntermediate(BaseModel):
    step_name: str
    enabled: bool
    success: bool
    image: str | None = None
    metadata: dict[str, Any]
    processing_time_ms: int


class PreviewPipelineResponse(BaseModel):
    intermediates: list[StepIntermediate]
    final_image: str
    total_processing_time_ms: int


class ExportPipelineRequest(BaseModel):
    steps: list[PipelineStepConfig]


class ExportPipelineResponse(BaseModel):
    yaml: str
```

#### 3. API Routes (`ocr_manga_title/api/routes/preprocess.py`)

4 endpoints, all under `prefix="/api/v1/preprocess"`:

| Method | Path | Input | Output |
|---|---|---|---|
| `GET` | `/steps` | — | `list[StepDescriptor]` |
| `POST` | `/preview/step` | multipart: image file + `PreviewStepRequest` JSON as form field | `PreviewStepResponse` |
| `POST` | `/preview/pipeline` | multipart: image file + `PreviewPipelineRequest` JSON as form field | `PreviewPipelineResponse` |
| `POST` | `/export` | JSON body: `ExportPipelineRequest` | `ExportPipelineResponse` |

**Image handling**:
- Decode: `cv2.imdecode(numpy.frombuffer(content, numpy.uint8), cv2.IMREAD_COLOR)`
- Encode result: `cv2.imencode(".png", image)[1].tobytes()` → base64 data URL

**Single step preview** (`POST /preview/step`):
1. Validate `step_name` exists in registry
2. Instantiate step class
3. Call `step.process(image, config)`
4. Encode result image to base64
5. Return `PreviewStepResponse`

**Pipeline preview** (`POST /preview/pipeline`):
1. Parse pipeline config into a lookup by step_name
2. Iterate `STEP_ORDER`
3. For each step: check if enabled in request config
   - If disabled: append `StepIntermediate(enabled=False)` with no image
   - If enabled: run step, append `StepIntermediate(enabled=True)` with base64 image
4. Pass previous output as next input (chaining)
5. Return all intermediates + final image

**Export** (`POST /export`):
1. Build YAML dict matching `config/preprocess.yaml` format:
```yaml
preprocessing:
  enabled: true
  debug: true
  roi:
    enabled: true
    method: contour
    min_area: 500
    ...
  grayscale:
    enabled: true
  ...
```
2. Return as string

**Validation**:
- Reject unknown step names (422)
- Validate config params against registry schema (422 for invalid values)

#### 4. Router Registration

In `ocr_manga_title/api/app.py`:
```python
from ocr_manga_title.api.routes import preprocess
app.include_router(preprocess.router, prefix="/api/v1/preprocess", tags=["preprocess"])
```

---

### Frontend

#### 1. API Client (`frontend/src/api/client.ts` additions)

```typescript
export interface StepParamDescriptor {
  type: string;
  default: any;
  options?: any[];
  min?: number;
  max?: number;
  step?: number;
}

export interface StepDescriptor {
  name: string;
  display_name: string;
  description: string;
  category: string;
  is_available: boolean;
  params: Record<string, StepParamDescriptor>;
}

export interface PreviewStepResponse {
  image: string;
  metadata: Record<string, any>;
  processing_time_ms: number;
}

export interface PipelineStepConfig {
  step_name: string;
  enabled: boolean;
  config: Record<string, any>;
}

export interface StepIntermediate {
  step_name: string;
  enabled: boolean;
  success: boolean;
  image: string | null;
  metadata: Record<string, any>;
  processing_time_ms: number;
}

export interface PreviewPipelineResponse {
  intermediates: StepIntermediate[];
  final_image: string;
  total_processing_time_ms: number;
}

export async function getPreprocessSteps(): Promise<StepDescriptor[]> { ... }
export async function previewStep(file: File, stepName: string, config: Record<string, any>): Promise<PreviewStepResponse> { ... }
export async function previewPipeline(file: File, steps: PipelineStepConfig[]): Promise<PreviewPipelineResponse> { ... }
export async function exportPipeline(steps: PipelineStepConfig[]): Promise<string> { ... }
```

#### 2. Components

**`ImageCompare.tsx`** — Side-by-side image display:
- Two equal-width columns, images scaled to same height
- Labels: "Original" / "Transformed"
- Empty state: "Upload an image to begin" / "Run a preview to see results"

**`PreprocessStepCard.tsx`** — Expandable accordion for a single step:
- Header: step display name + enabled toggle (for pipeline)
- Body (when expanded): dynamic parameter form rendered from `StepParamDescriptor`
  - `select` → `<select>` dropdown
  - `int` / `float` → range slider with min/max/step + numeric readout
  - `bool` → toggle switch
- Actions: **Preview** (runs single step), **Add to Pipeline** (enables step with current params)

**`PipelineFilmstrip.tsx`** — Horizontal scrollable strip:
- One thumbnail per step in canonical order
- Each thumbnail: step name label + image (or "skipped" placeholder)
- Arrows between steps showing flow direction
- Highlights the final output

#### 3. Playground Page (`PreprocessPlayground.tsx`)

**Layout**:

```
┌─────────────────────────────────────────────────────────────────┐
│  Preprocessing Playground              [Upload Image]           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ Step Toolbox (accordion, canonical order) ───────────────┐  │
│  │  ┌─ Region of Interest ───────────────────────────────┐   │  │
│  │  │  method: [contour ▾]  min_area: [====■===] 500     │   │  │
│  │  │  padding: [==■=====] 10   merge: [===■==] 0.3      │   │  │
│  │  │  [Preview]  [✚ Add to Pipeline]                     │   │  │
│  │  └────────────────────────────────────────────────────┘   │  │
│  │  ▸ Grayscale    ▸ Upscale    ▸ Denoise    ▸ Binarize     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌────────────────────┬────────────────────────────────────┐    │
│  │    Original        │        Transformed                 │    │
│  │                    │                                    │    │
│  └────────────────────┴────────────────────────────────────┘    │
│                                                                 │
│  ── Pipeline Preview ──────────────────────────────────────────  │
│  [✓ ROI]  [✓ Grayscale]  [✗ Upscale]  [✓ Denoise]  [✓ Bin.]  │
│  [Run Pipeline]   [Export YAML]                                  │
│                                                                 │
│  Filmstrip:                                                      │
│  [original] → [after roi] → [after gray] → [after denoise]      │
│             → [after binarize]                                   │
└─────────────────────────────────────────────────────────────────┘
```

**State model**:

```typescript
interface PlaygroundState {
  steps: StepDescriptor[];                                     // from API
  originalFile: File | null;                                   // uploaded image
  originalPreview: string | null;                              // base64 preview
  stepConfigs: Record<string, Record<string, any>>;            // current param values per step
  pipelineEnabled: Record<string, boolean>;                    // which steps are in the pipeline
  singlePreview: PreviewStepResponse | null;                   // last single-step result
  pipelineResult: PreviewPipelineResponse | null;              // last pipeline result
  loading: boolean;
  error: string | null;
}
```

**UX flow**:
1. User uploads image → original appears in left panel
2. User clicks a step accordion → parameter form appears → clicks **Preview** → transformed image appears in right panel
3. User clicks **Add to Pipeline** → step toggles on in pipeline section
4. Pipeline section shows all 5 steps as toggles (canonical order). User adjusts params per step.
5. User clicks **Run Pipeline** → filmstrip shows intermediate result after each enabled step
6. User clicks **Export YAML** → downloads `preprocess.yaml`

---

## Implementation Steps

### Step 1: Step Registry

**Task**: Create `ocr_manga_title/preprocess/registry.py` with step descriptors and `get_step_descriptors()`.

**File**: `ocr_manga_title/preprocess/registry.py`

### Step 2: API Schemas

**Task**: Create `ocr_manga_title/api/schemas/preprocess.py` with all request/response models.

**File**: `ocr_manga_title/api/schemas/preprocess.py`

### Step 3: API Routes

**Task**: Create `ocr_manga_title/api/routes/preprocess.py` with 4 endpoints.

**Files**: 
- `ocr_manga_title/api/routes/preprocess.py` (new)
- `ocr_manga_title/api/app.py` (register router)
- `ocr_manga_title/api/schemas/__init__.py` (export schemas)

### Step 4: Backend Tests

**Task**: Write ~10 tests covering all endpoints.

**File**: `tests/test_api/test_preprocess.py`

### Step 5: Frontend API Client

**Task**: Add 4 API functions and TypeScript types to `frontend/src/api/client.ts`.

**File**: `frontend/src/api/client.ts`

### Step 6: Shared Components

**Task**: Create 3 new components.

**Files**:
- `frontend/src/components/ImageCompare.tsx`
- `frontend/src/components/PreprocessStepCard.tsx`
- `frontend/src/components/PipelineFilmstrip.tsx`

### Step 7: Playground Page + Routing

**Task**: Create the main page and add routing.

**Files**:
- `frontend/src/pages/PreprocessPlayground.tsx` (new)
- `frontend/src/App.tsx` (add route + NavLink)

### Step 8: Verify

**Task**: Run full test suite, lint, frontend build.

---

## Acceptance Criteria

- [ ] `GET /api/v1/preprocess/steps` returns 5 step descriptors with param schemas
- [ ] `POST /api/v1/preprocess/preview/step` applies a single step and returns base64 image
- [ ] `POST /api/v1/preprocess/preview/pipeline` applies ordered steps and returns all intermediates
- [ ] `POST /api/v1/preprocess/export` generates valid YAML matching `preprocess.yaml` format
- [ ] Invalid step names return 422
- [ ] Step order is always canonical: roi → grayscale → upscale → denoise → binarize
- [ ] Pipeline preview returns one intermediate per step (including disabled steps as skipped)
- [ ] `/playground` page renders in the frontend with image upload
- [ ] Side-by-side original vs transformed image display works
- [ ] Step parameter forms render dynamically from API schema (select, range, bool)
- [ ] Pipeline filmstrip shows intermediate images for each enabled step
- [ ] Export downloads a YAML file compatible with `config/preprocess.yaml`
- [ ] All existing 258 tests still pass
- [ ] Ruff lint clean on new Python files
- [ ] Frontend TypeScript clean, Vite build succeeds
