# Phase Definitions — Manga OCR

This document defines every phase of the Manga OCR project with enough detail for an implementation agent to write rich, precise user stories and execute them without ambiguity.

Each phase includes: scope boundaries, capabilities delivered, technical specifications, component inventory, data models, integration contracts, error scenarios, and explicit exclusions.

---

## Phase 0: OCR Engine Module

**Status**: Planned
**Prerequisite**: None
**Delivers**: Standalone Python package that takes an image path and returns structured manga metadata

### Scope

A single Python package (`manga_ocr/`) with no external services, no API server, no database, no frontend. All interaction via Python imports, CLI entry point, or Jupyter notebook.

### Sub-Phases

#### 0A — Foundation (Config, Schemas, Interfaces)

**Capabilities**:
- Load and validate `configs.toml` (OpenRouter API key, default model, base URL, images_path)
- Load and validate `ocrs.yaml` (per-model: enabled, language, parameters)
- Pydantic schemas for all data types used across the entire pipeline
- Abstract base class `BaseOCRModel` defining the contract all OCR models implement
- Custom exception hierarchy: `MangaOCRError`, `ConfigurationError`, `ModelNotAvailableError`, `LLMExtractionError`

**Data Models** (Pydantic v2):

```
AppConfig:
  images_path: Path
  openrouter: OpenRouterConfig

OpenRouterConfig:
  api_key: str
  default_model: str = "google/gemini-2.5-flash"
  base_url: str = "https://openrouter.ai/api/v1"

ModelConfig:
  name: str
  enabled: bool = True
  language: str | list[str]
  parameters: dict[str, Any] = {}

OCRResult:
  raw_text: str
  model_name: str
  confidence: float          # 0.0 - 1.0
  processing_time_ms: int
  error: str | None = None   # populated if model failed

ExtractedTitle:
  title_en: str | None
  title_ja: str | None
  code: str | None
  confidence: float = 0.0
  source_model: str = ""
  source_method: str = ""    # "llm" | "rules" | "llm+rules"

PipelineResult:
  input_path: str
  ocr_results: list[OCRResult]
  extracted: ExtractedTitle | None
  timestamp: datetime
  errors: list[str] = []
```

**Files**:
- `manga_ocr/__init__.py`
- `manga_ocr/config.py`
- `manga_ocr/schemas.py`
- `manga_ocr/exceptions.py`
- `manga_ocr/models/base.py`
- `manga_ocr/models/__init__.py`
- `tests/test_config.py`
- `tests/test_schemas.py`

**Config File Formats**:

`configs.toml`:
```toml
images_path = "/Users/rconsuegra/Pictures"

[openrouter]
api_key = "sk-or-..."
default_model = "google/gemini-2.5-flash"
base_url = "https://openrouter.ai/api/v1"
```

`ocrs.yaml`:
```yaml
models:
  manga_ocr:
    enabled: true
    language: ja
  tesseract:
    enabled: true
    languages: ["eng", "jpn"]
    psm: 3
    oem: 3
  paddle:
    enabled: false
    languages: ["en", "ja"]
  easyocr:
    enabled: false
    languages: ["en", "ja"]
  glm_ocr:
    enabled: false
    api_endpoint: ""
```

**Validation Rules**:
- `openrouter.api_key` is required, must start with `sk-`
- `images_path` must exist on disk (checked at load time, warn if missing)
- Unknown model names in `ocrs.yaml` are logged as warnings but not errors
- If a model block is missing `enabled`, default to `True`

**Base Model Interface** (`manga_ocr/models/base.py`):

```
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

---

#### 0B — OCR Models (manga-ocr, Tesseract, Stubs)

**Capabilities**:
- manga-ocr model wrapper: loads `kha-white/manga-ocr-simplified` from HuggingFace, lazy-loaded on first `run()` call
- Tesseract model wrapper: wraps `pytesseract` with configurable language packs, PSM/OEM modes
- Stub models for PaddleOCR, EasyOCR, GLM OCR: `is_available=False`, `run()` raises `NotImplementedError`

**manga-ocr Wrapper** (`manga_ocr/models/manga_ocr_model.py`):
- Lazy model loading: `MangaOCRModel()` constructor does NOT load the model; first call to `run()` triggers load
- Uses `transformers` pipeline under the hood (manga-ocr is a HuggingFace model)
- Accepts PNG, JPG, WEBP; converts to PIL Image internally
- Returns `OCRResult` with `model_name="manga-ocr"`, `confidence` estimated from output (if available) or default `0.7`
- On first load: downloads model weights to HuggingFace cache (`~/.cache/huggingface/`); logs progress
- On subsequent loads: reuses in-memory model instance (singleton per process)
- Handles: corrupt images (return `OCRResult` with empty text, low confidence, error message), missing model files (raise `ModelNotAvailableError`)

**Tesseract Wrapper** (`manga_ocr/models/tesseract_model.py`):
- Uses `pytesseract.image_to_string()` and `pytesseract.image_to_data()` (for confidence)
- Language packs: `["eng", "jpn"]` by default, read from `ocrs.yaml` `languages` field
- PSM (Page Segmentation Mode): configurable via `ocrs.yaml` `psm` parameter (default 3 = fully automatic)
- OEM (OCR Engine Mode): configurable via `ocrs.yaml` `oem` parameter (default 3 = default, based on what's available)
- Confidence: computed as mean of word-level confidences from `image_to_data()`, excluding words with confidence < 30
- Handles: missing Tesseract binary (raise `ModelNotAvailableError` with install instructions), missing language packs (raise with download instructions)

**Stub Models** (each in `manga_ocr/models/{name}_model.py`):
- `name` property returns the model identifier string
- `is_available` property returns `False`
- `run()` raises `NotImplementedError(f"{self.name} integration not yet implemented")`
- Constructor accepts `ModelConfig` for forward compatibility

**Files**:
- `manga_ocr/models/manga_ocr_model.py`
- `manga_ocr/models/tesseract_model.py`
- `manga_ocr/models/paddle_model.py`
- `manga_ocr/models/easyocr_model.py`
- `manga_ocr/models/glm_ocr_model.py`
- `tests/test_models.py`

**Test Strategy**:
- Model interface compliance: test that each model class implements `name`, `is_available`, `run()`
- Stub models: verify `is_available=False`, verify `run()` raises `NotImplementedError`
- manga-ocr and Tesseract: mock the underlying library calls, verify `OCRResult` structure
- No test requires actual model weights or a running Tesseract binary

---

#### 0C — Post-Processing (LLM Extractor, Rule Matcher)

**Capabilities**:
- LLM extractor: sends raw OCR text to OpenRouter via OpenAI SDK, parses response into `ExtractedTitle`
- Rule matcher: detects ISBN-10, ISBN-13, manga-specific codes via regex; normalizes titles

**LLM Extractor** (`manga_ocr/postprocess/llm_extractor.py`):

```
class LLMExtractor:
    def __init__(self, config: OpenRouterConfig, prompt_path: Path | None = None): ...
    def extract(self, raw_text: str, model: str | None = None) -> ExtractedTitle: ...
```

- Uses `openai` Python SDK with `base_url` set to OpenRouter
- Model ID: from constructor arg, falling back to `config.default_model`
- Prompt: loaded from `prompts/llm/extract_title_v1.md` (or custom path)
- Prompt structure: system message (instructions) + user message (raw OCR text)
- LLM response must be valid JSON matching `ExtractedTitle` schema
- If LLM returns non-JSON: attempt to extract JSON from markdown code blocks; if that fails, return `ExtractedTitle(confidence=0.0)` with error logged
- If API call fails (timeout, rate limit, auth error): return `ExtractedTitle(confidence=0.0, source_method="llm_failed")` with error logged; do NOT raise
- Token usage and latency logged at DEBUG level

**Rule Matcher** (`manga_ocr/postprocess/rule_matcher.py`):

```
class RuleMatcher:
    def match(self, text: str) -> ExtractedTitle: ...
    def augment(self, existing: ExtractedTitle, text: str) -> ExtractedTitle: ...
```

- ISBN-10 regex: `r'(?:ISBN[- ]?)?(?:\d[\s-]?){9}[\dXx]'`
- ISBN-13 regex: `r'(?:ISBN[- ]?)?97[89](?:[\s-]?\d){10}'`
- Normalized ISBN: stripped of hyphens and spaces for storage
- Title normalization: collapse whitespace, trim, normalize unicode (NFC), strip trailing punctuation
- `match()`: scans text, returns `ExtractedTitle` with any found codes
- `augment()`: takes existing `ExtractedTitle` from LLM, fills in `None` fields with rule-based findings (rules do NOT overwrite LLM results that are already populated)

**Prompt File** (`prompts/llm/extract_title_v1.md`):
- System prompt instructing the LLM to extract manga metadata from raw OCR text
- Must handle: noisy OCR output, partial text, mixed EN+JA, multiple titles in one image
- Must return valid JSON: `{"title_en": "...", "title_ja": "...", "code": "...", "confidence": 0.0-1.0}`
- Must instruct: if no manga title found, return all fields as null with confidence 0.0

**Files**:
- `manga_ocr/postprocess/__init__.py`
- `manga_ocr/postprocess/llm_extractor.py`
- `manga_ocr/postprocess/rule_matcher.py`
- `prompts/llm/extract_title_v1.md`
- `tests/test_postprocess.py`

**Test Strategy**:
- LLM extractor: mock `openai.OpenAI` client, verify request structure, verify response parsing, verify error handling (invalid JSON, API error, timeout)
- Rule matcher: unit tests with known text inputs — ISBN-10 present, ISBN-13 present, no codes, multiple codes, Japanese text with embedded codes
- Augment: verify LLM results are preserved, rule findings fill gaps

---

#### 0D — Pipeline Orchestrator

**Capabilities**:
- Coordinate the full pipeline: image -> OCR models -> LLM -> rules -> structured result
- Graceful degradation: continue if individual models or LLM fail
- Model selection based on `ocrs.yaml` enabled flags and model availability

**Engine** (`manga_ocr/engine.py`):

```
class OCREngine:
    def __init__(self, config: AppConfig, ocr_config: dict[str, ModelConfig]): ...
    def process(self, image_path: str) -> PipelineResult: ...
```

**Process Flow**:
1. Validate `image_path` exists and is a supported format (PNG, JPG, WEBP, TIFF, BMP)
2. Initialize enabled + available models (log skipped models: disabled, unavailable stubs)
3. For each enabled model, call `model.run(image_path)`:
   - Wrap in try/except; on failure, add to `OCRResult` with error message, continue
   - Record processing time per model
4. Collect all `OCRResult`s (successful and failed)
5. For each successful `OCRResult` with non-empty `raw_text`:
   - Call `LLMExtractor.extract(raw_text)` -> `ExtractedTitle`
   - Call `RuleMatcher.augment(extracted, raw_text)` -> enhanced `ExtractedTitle`
6. Select best result: highest `confidence` across all extracted titles
7. Build and return `PipelineResult`

**Error Handling Matrix**:

| Scenario | Behavior |
|----------|----------|
| Image file does not exist | Raise `FileNotFoundError` with path |
| Image file is corrupt/unreadable | Log error, return `PipelineResult` with empty results, error in `errors` list |
| Single OCR model fails | Log error, continue with other models, failed model gets `OCRResult(error=...)` |
| All OCR models fail | Return `PipelineResult` with empty `ocr_results`, `extracted=None`, errors listed |
| LLM fails for one model's output | Log error, skip that extraction, continue with others |
| LLM fails for all outputs | `extracted` populated from rule matcher only (if codes found in raw text) |
| All post-processing fails | `extracted=None`, raw OCR results still available in `PipelineResult` |

**Files**:
- `manga_ocr/engine.py`
- `tests/test_engine.py`

**Test Strategy**:
- Full pipeline with all models mocked: verify `PipelineResult` structure
- Partial failure: one model raises, verify others still run
- Total failure: all models raise, verify graceful result
- LLM failure: mock LLM to raise, verify rule matcher still runs
- Image validation: non-existent path, unsupported format

---

#### 0E — Tests, Notebook, CLI

**Capabilities**:
- Complete test suite runnable via `make test`
- Jupyter notebook for interactive pipeline testing
- CLI entry point for running the pipeline from command line

**Test Suite** (`tests/`):
- `test_config.py`: valid config, missing config file, missing required fields, unknown fields, default values
- `test_schemas.py`: Pydantic model validation, serialization/deserialization, edge cases
- `test_models.py`: interface compliance for all models, stub behavior, mocked manga-ocr and Tesseract
- `test_postprocess.py`: LLM extractor with mocked API, rule matcher patterns, augment logic
- `test_engine.py`: full pipeline with all mocks, partial failures, edge cases

**Notebook** (`notebooks/01_ocr_testing.ipynb`):
- Section 1: Load config, display loaded settings
- Section 2: Run manga-ocr on a sample image, display raw text
- Section 3: Run Tesseract on the same image, compare output
- Section 4: Run LLM extractor on raw text, display `ExtractedTitle`
- Section 5: Run rule matcher, display findings
- Section 6: Run full pipeline via `OCREngine.process()`, display `PipelineResult`
- Section 7: Batch test — process multiple images and compare results in a table

**CLI** (`main.py`):
- Accept image path as CLI argument
- Load config, run pipeline, print result as formatted JSON
- Exit code 0 on success, 1 on error
- Usage: `python main.py path/to/image.png`

**Makefile Targets**:
- `make run`: run `main.py` with a hardcoded sample image (or fail gracefully if no sample)
- `make test`: run `pytest tests/ -v`
- `make lint`: run `ruff check .` and `ruff format --check .`
- `make notebook`: launch `jupyter notebook notebooks/`
- `make setup`: install dependencies via `uv sync`

---

### Phase 0 Exclusions

- No FastAPI server or REST endpoints
- No React frontend
- No PostgreSQL database or ORM
- No Dramatiq/Redis task queue
- No Agenta.ai integration (prompts loaded from local files only)
- No social media URL fetching (local images only)
- No image preprocessing pipeline (resizing, contrast enhancement, rotation correction)
- No model warmup/health-check endpoint
- No persistent result storage beyond the in-memory `PipelineResult`
- No batch processing API (notebook only)
- No logging to file (stdout/stderr only)

---

## Phase 1: MVP Backend API

**Status**: Future
**Prerequisite**: Phase 0 complete
**Delivers**: FastAPI server with manual image upload, pipeline execution via task queue, result storage in PostgreSQL, minimal React frontend

### Scope

A FastAPI backend that wraps the Phase 0 OCR engine, adds persistent storage via PostgreSQL, async job processing via Dramatiq + Redis, and a minimal React frontend for uploading images and viewing results.

### Sub-Phases

#### 1A — Database Layer

**Capabilities**:
- PostgreSQL schema with Alembic migrations
- SQLAlchemy 2.0 async ORM models
- CRUD operations for all entities

**Database Schema**:

```
pipeline_runs:
  id: UUID (PK)
  input_image_path: str (not null)
  source_url: str | null
  source_platform: str | null          # "twitter" | "facebook" | "manual"
  status: str (not null, default="pending")  # "pending" | "processing" | "completed" | "failed"
  error_message: str | null
  created_at: datetime (not null)
  completed_at: datetime | null

ocr_results:
  id: UUID (PK)
  pipeline_run_id: UUID (FK -> pipeline_runs.id, not null)
  model_name: str (not null)
  raw_text: text (not null)
  confidence: float (not null)
  processing_time_ms: int (not null)
  error: str | null
  created_at: datetime (not null)

post_processing_results:
  id: UUID (PK)
  ocr_result_id: UUID (FK -> ocr_results.id, not null)
  prompt_version_id: UUID (FK -> prompt_versions.id, null)  # null for Phase 1 since no Agenta yet
  title_en: str | null
  title_ja: str | null
  code: str | null
  confidence: float (not null)
  processing_type: str (not null)       # "llm" | "rules" | "llm+rules"
  created_at: datetime (not null)

prompt_versions:
  id: UUID (PK)
  prompt_type: str (not null)           # "ocr" | "llm"
  content: text (not null)
  version_number: int (not null)
  agenta_id: str | null
  is_active: bool (default=false)
  tags: str | null                      # comma-separated for simplicity, or JSONB
  created_at: datetime (not null)

catalog_entries:
  id: UUID (PK)
  title_en: str | null
  title_ja: str | null
  code: str | null
  source_run_id: UUID (FK -> pipeline_runs.id, not null)
  confidence: float (not null)
  status: str (default="needs_review")  # "auto_confirmed" | "needs_review" | "rejected"
  created_at: datetime (not null)
  updated_at: datetime | null

model_configs:
  id: UUID (PK)
  model_name: str (not null, unique)
  is_enabled: bool (default=true)
  parameters: JSONB
  language_hint: str | null
  updated_at: datetime (not null)
```

**Alembic Migrations**:
- Initial migration: all tables above
- Seed migration: populate `model_configs` from `ocrs.yaml` defaults
- Seed migration: insert `prompt_versions` from local `prompts/llm/extract_title_v1.md`

**Files**:
- `alembic.ini`
- `migrations/` (Alembic directory with versions/)
- `manga_ocr/db/__init__.py`
- `manga_ocr/db/models.py` (SQLAlchemy ORM models)
- `manga_ocr/db/session.py` (async session factory)
- `manga_ocr/db/crud.py` (CRUD operations)

---

#### 1B — FastAPI Application

**Capabilities**:
- FastAPI app with async routes
- OpenAPI documentation auto-generated
- Request/response validation via Pydantic
- CORS configured for local frontend development

**API Routes**:

Input endpoints:
- `POST /api/v1/inputs/upload` — multipart form, accepts 1-10 images, saves to `images_path`, creates `pipeline_runs` records with status "pending"
- `GET /api/v1/inputs/{run_id}` — returns pipeline run status and results (if completed)

Pipeline endpoints:
- `POST /api/v1/pipeline/run/{run_id}` — enqueues a Dramatiq job for the given pipeline run
- `GET /api/v1/pipeline/runs` — list pipeline runs, paginated (default 20 per page), sortable by created_at, filterable by status
- `GET /api/v1/pipeline/runs/{run_id}` — full run details including all OCR results and post-processing results

Results endpoints:
- `GET /api/v1/results` — list post-processing results, filterable by model_name, confidence range, date range
- `PUT /api/v1/results/{id}/override` — manual correction: update title_en, title_ja, code; marks catalog entry as "ground_truth"

Catalog endpoints:
- `GET /api/v1/catalog` — list catalog entries, searchable by title/code, filterable by status, paginated
- `GET /api/v1/catalog/{id}` — single catalog entry detail
- `PUT /api/v1/catalog/{id}` — update entry status (auto_confirmed / needs_review / rejected)
- `GET /api/v1/catalog/export` — export all catalog entries as CSV download

Model endpoints:
- `GET /api/v1/models` — list all model configs with current is_enabled status
- `PUT /api/v1/models/{model_name}` — update model config (enable/disable, change parameters)

**App Structure**:
- `manga_ocr/api/__init__.py`
- `manga_ocr/api/app.py` (FastAPI app factory)
- `manga_ocr/api/routes/__init__.py`
- `manga_ocr/api/routes/inputs.py`
- `manga_ocr/api/routes/pipeline.py`
- `manga_ocr/api/routes/results.py`
- `manga_ocr/api/routes/catalog.py`
- `manga_ocr/api/routes/models.py`
- `manga_ocr/api/dependencies.py` (dependency injection: db session, config)
- `manga_ocr/api/schemas.py` (request/response Pydantic models, separate from engine schemas)

**Error Responses**:
- All errors return JSON: `{"detail": "...", "error_code": "..."}`
- 400: invalid input (bad image format, missing fields)
- 404: resource not found (run_id, result_id, catalog_id)
- 422: validation errors (Pydantic automatic)
- 500: unexpected server errors (logged, no stack trace in response)

---

#### 1C — Task Queue (Dramatiq + Redis)

**Capabilities**:
- Dramatiq actor that runs the OCR pipeline for a given pipeline_run_id
- Redis as message broker
- Retry logic: 3 attempts with exponential backoff for transient failures
- Worker process separate from API server

**Job Flow**:
1. API receives `POST /api/v1/pipeline/run/{run_id}`
2. API updates `pipeline_runs.status` to "pending", enqueues Dramatiq message with `run_id`
3. Dramatiq worker picks up message
4. Worker updates status to "processing"
5. Worker calls `OCREngine.process(image_path)`
6. Worker stores `ocr_results` rows for each model output
7. Worker stores `post_processing_results` rows for LLM + rule outputs
8. Worker creates `catalog_entries` row if extracted title is not None
9. Worker updates `pipeline_runs.status` to "completed" (or "failed" with error_message)
10. API polls `GET /api/v1/pipeline/runs/{run_id}` to check status

**Retry Policy**:
- LLM API errors (5xx, timeout): retry up to 3 times, backoff 10s/30s/60s
- OCR model errors: do NOT retry (model error is captured in OCRResult, pipeline continues)
- Database errors: retry up to 2 times
- Max message age: 1 hour (reject stale jobs)

**Files**:
- `manga_ocr/workers/__init__.py`
- `manga_ocr/workers/ocr_worker.py` (Dramatiq actor)
- `manga_ocr/workers/broker.py` (Redis broker configuration)

---

#### 1D — Minimal React Frontend

**Capabilities**:
- Single-page React + TypeScript app (Vite)
- Upload form: drag-and-drop or file picker, submit 1-10 images
- Results table: list of pipeline runs with status, click to expand details
- Run detail view: input image thumbnail, OCR results per model, extracted title, confidence
- Catalog view: table of all catalog entries, searchable, status filter

**Pages**:
- `/` — Dashboard: recent pipeline runs, quick stats (total processed, success rate)
- `/upload` — Upload form
- `/runs` — Pipeline runs list
- `/runs/:id` — Run detail
- `/catalog` — Catalog entries list

**Components**:
- `ImageUploader` — drag-and-drop with preview
- `RunStatusBadge` — pending/processing/completed/failed
- `ResultsTable` — sortable, filterable table
- `CatalogTable` — searchable, filterable with status toggles
- `ConfidenceMeter` — visual confidence indicator (color-coded bar)

**Tech**:
- React 18 + TypeScript
- Vite for build
- Tailwind CSS for styling (or plain CSS — keep it minimal)
- No state management library (React useState + fetch)
- No routing library needed for v1 (tabs or simple conditional rendering)

**Files**:
- `frontend/` directory (separate from Python package)
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/` (standard React app structure)

---

### Phase 1 Exclusions

- No social media URL fetching (manual upload only)
- No Agenta.ai integration (prompts from DB, loaded from seed migration)
- No pipeline visualization (just status badges)
- No results comparison view (just a flat table)
- No WebSocket updates (polling only)
- No authentication
- No Docker (runs locally)
- No evaluation/gold standard system

---

## Phase 2: Multi-Model + Prompt Management

**Status**: Future
**Prerequisite**: Phase 1 complete
**Delivers**: All OCR models implemented, Agenta.ai prompt sync, prompt CRUD UI, pipeline visualization, social media URL input

### Sub-Phases

#### 2A — Additional OCR Models

**Capabilities**:
- PaddleOCR wrapper: local model, EN + JA, configurable via `ocrs.yaml`
- EasyOCR wrapper: local model, EN + JA, GPU optional
- GLM OCR wrapper: API-based OCR model, requires API endpoint config

**PaddleOCR Wrapper** (`manga_ocr/models/paddle_model.py`):
- Uses `paddleocr` Python package
- Lazy initialization on first `run()`
- Configurable: languages, use_gpu flag, det_model_dir, rec_model_dir
- Returns `OCRResult` with confidence from PaddleOCR's built-in scoring
- Handles: CUDA not available (fallback to CPU), model download on first use
- `is_available` becomes dynamic: checks if `paddleocr` package is importable and model weights exist

**EasyOCR Wrapper** (`manga_ocr/models/easyocr_model.py`):
- Uses `easyocr` Python package
- Lazy initialization: `easyocr.Reader(['en', 'ja'])` on first `run()`
- Returns `OCRResult` with per-word confidence averaged
- Configurable: languages, GPU flag, model_storage_directory
- `is_available` becomes dynamic: checks if `easyocr` package is importable

**GLM OCR Wrapper** (`manga_ocr/models/glm_ocr_model.py`):
- API-based: sends image as base64 to GLM OCR endpoint
- Endpoint URL from `ocrs.yaml` `api_endpoint` field
- Requires API key (stored in `configs.toml`)
- Returns `OCRResult` with raw text and confidence from API response
- Handles: API errors, timeout, rate limiting
- `is_available` becomes dynamic: checks if `api_endpoint` is configured and reachable

**Transition from Stubs**:
- Remove stub implementations from Phase 0
- Replace with working wrappers
- `is_available` transitions from hardcoded `False` to dynamic checks (library installed, weights exist, API reachable)
- Existing tests updated: stub tests replaced with mocked integration tests

---

#### 2B — Agenta.ai Integration

**Capabilities**:
- Bidirectional prompt sync with Agenta.ai
- Agenta.ai is source of truth for prompt content and versions
- Local `prompts/` directory serves as cache/fallback
- Sync triggered manually via API endpoint or on app startup

**Agenta Client** (`manga_ocr/agenta_client.py`):
- Pull: fetch all prompt versions from Agenta.ai, upsert into `prompt_versions` table
- Push: create/update prompt version in Agenta.ai from local edit
- Conflict resolution: Agenta version wins if timestamps differ
- Offline fallback: if Agenta.ai is unreachable, use local `prompts/` files and cached DB versions

**API Endpoints Added**:
- `GET /api/v1/prompts` — list all prompt versions, filterable by prompt_type, is_active
- `POST /api/v1/prompts` — create new prompt version (pushes to Agenta.ai)
- `GET /api/v1/prompts/{id}` — get prompt version content
- `PUT /api/v1/prompts/{id}` — update prompt version (pushes to Agenta.ai)
- `DELETE /api/v1/prompts/{id}` — delete prompt version (deactivates in Agenta.ai)
- `POST /api/v1/prompts/{id}/activate` — set as active prompt for its type
- `POST /api/v1/prompts/sync` — trigger sync from Agenta.ai
- `GET /api/v1/prompts/{id}/diff/{other_id}` — diff between two prompt versions

**Frontend Pages Added**:
- `/prompts` — Prompt list with filter by type (OCR/LLM)
- `/prompts/new` — Create prompt form with markdown editor
- `/prompts/:id` — View prompt content, version history
- `/prompts/:id/diff` — Select two versions to compare

**Files**:
- `manga_ocr/agenta_client.py`
- `manga_ocr/api/routes/prompts.py`
- `frontend/src/pages/Prompts.tsx`
- `frontend/src/pages/PromptDetail.tsx`
- `frontend/src/pages/PromptDiff.tsx`
- `frontend/src/components/PromptEditor.tsx`

---

#### 2C — Pipeline Visualization

**Capabilities**:
- Static pipeline diagram showing all stages
- Per-node configuration display
- Real-time status updates (polling, not WebSocket yet)

**Frontend Component**: `PipelineDiagram`
- Directed graph rendered with a React diagram library (e.g., reactflow or elkjs)
- Nodes: Input -> OCR models (one per enabled model) -> Raw Text Merge -> LLM -> Rules -> Output
- Each node clickable: shows config panel with model name, prompt version, parameters
- Status colors: gray (idle), blue (processing), green (completed), red (error)
- Updates on poll interval (every 5 seconds while a run is in progress)

**Files**:
- `frontend/src/components/PipelineDiagram.tsx`
- `frontend/src/components/NodeConfigPanel.tsx`

---

#### 2D — Social Media URL Input

**Capabilities**:
- Accept X/Twitter post URL, extract image from tweet
- Accept Facebook post URL, extract image from post
- Image stored locally, pipeline run created with `source_platform` and `source_url` populated

**X/Twitter Integration** (`manga_ocr/social/twitter.py`):
- Use Twitter/X API (or scraping fallback) to fetch tweet media
- Extract primary image (first image in tweet)
- Handle: protected tweets (error), deleted tweets (error), tweets with no image (error)
- Rate limiting: respect API limits, queue requests

**Facebook Integration** (`manga_ocr/social/facebook.py`):
- Use Facebook Graph API to fetch post attachments
- Extract image from post
- Handle: private posts (error), posts with no image (error)

**API Endpoint**:
- `POST /api/v1/inputs/url` — body: `{url: string, platform?: string}`, auto-detects platform if not specified

**Frontend**:
- URL input field on upload page (tab: "Upload File" / "From URL")
- Platform auto-detection with manual override
- Preview extracted image before submitting to pipeline

**Files**:
- `manga_ocr/social/__init__.py`
- `manga_ocr/social/twitter.py`
- `manga_ocr/social/facebook.py`
- `manga_ocr/api/routes/inputs.py` (updated)
- `frontend/src/components/UrlInput.tsx`

---

### Phase 2 Exclusions

- No results comparison view (Phase 3)
- No evaluation system (Phase 3)
- No WebSocket real-time updates (Phase 4)
- No Docker deployment (Phase 4)

---

## Phase 3: Evaluation & Comparison

**Status**: Future
**Prerequisite**: Phase 2 complete
**Delivers**: Gold standard dataset, results comparison viewer, evaluation pipeline, manual corrections, catalog management

### Sub-Phases

#### 3A — Gold Standard & Evaluation

**Capabilities**:
- Upload and label images with expected manga title/code
- Run evaluation: process gold standard images with current pipeline config, compare against expected results
- Calculate per-model and per-prompt accuracy metrics

**Gold Standard Management**:
- Upload image + manually enter expected: title_en, title_ja, code
- Store in `gold_standard` table:
  ```
  gold_standard:
    id: UUID (PK)
    image_path: str (not null)
    expected_title_en: str | null
    expected_title_ja: str | null
    expected_code: str | null
    created_at: datetime (not null)
    updated_at: datetime | null
  ```
- Minimum 50 labeled images for meaningful evaluation
- Gold standard images excluded from regular catalog (flagged)

**Evaluation Pipeline**:
- `POST /api/v1/eval/run` — triggers evaluation run:
  1. For each gold_standard entry, run pipeline (same as normal)
  2. Compare extracted result against expected values
  3. Calculate: exact match %, partial match % (title correct but code wrong, etc.)
  4. Break down by model, by prompt version
  5. Store evaluation results for historical comparison
- `GET /api/v1/eval/results` — returns latest evaluation metrics and historical trend

**Evaluation Results Storage**:
```
evaluation_runs:
  id: UUID (PK)
  triggered_at: datetime (not null)
  completed_at: datetime | null
  total_images: int (not null)
  exact_match_count: int (not null)
  title_match_count: int (not null)
  code_match_count: int (not null)
  per_model_metrics: JSONB         # {"manga-ocr": {...}, "tesseract": {...}}
  per_prompt_metrics: JSONB        # {"v1": {...}, "v2": {...}}

evaluation_details:
  id: UUID (PK)
  eval_run_id: UUID (FK -> evaluation_runs.id)
  gold_standard_id: UUID (FK -> gold_standard.id)
  pipeline_run_id: UUID (FK -> pipeline_runs.id)
  exact_match: bool
  title_en_match: bool
  title_ja_match: bool
  code_match: bool
  best_model: str | null
```

**Accuracy Metrics**:
- Exact match: title_en + title_ja + code all correct
- Title-only match: at least one title matches (case-insensitive, unicode-normalized)
- Code match: ISBN/code matches (normalized: stripped hyphens/spaces)
- Per-model contribution: which model produced the best result per image
- Per-prompt contribution: which prompt version produced the best result

**Files**:
- `manga_ocr/db/models.py` (updated: add gold_standard, evaluation_runs, evaluation_details tables)
- `manga_ocr/evaluation/__init__.py`
- `manga_ocr/evaluation/runner.py` (evaluation pipeline logic)
- `manga_ocr/evaluation/metrics.py` (accuracy calculation)
- `manga_ocr/api/routes/evaluation.py`
- `frontend/src/pages/Evaluation.tsx`
- `frontend/src/components/GoldStandardUploader.tsx`
- `frontend/src/components/MetricsDashboard.tsx`

---

#### 3B — Results Comparison Viewer

**Capabilities**:
- Side-by-side comparison of OCR results for the same input image across different models and prompt versions
- Diff view for raw text and extracted titles
- Confidence score visualization

**Frontend Component**: `ResultsComparison`
- Select an input image (or pipeline run)
- Display grid: rows = models, columns = prompt versions
- Each cell shows: raw text (truncated), extracted title, confidence bar
- Highlight differences between cells
- Click cell to expand full raw text and extraction details
- Filter: select specific models and prompt versions to compare

**Raw Text Diff**:
- Line-by-line diff between two raw text outputs
- Highlight: additions (green), deletions (red), modifications (yellow)
- Character-level diff for short texts, line-level for long texts

**Extracted Title Diff**:
- Field-by-field comparison: title_en, title_ja, code, confidence
- Visual indicator: green (match), red (mismatch), gray (null/missing)

**API Endpoints**:
- `GET /api/v1/results/compare?run_id=...` — returns all results for a given run grouped by model
- `GET /api/v1/results/compare?image_hash=...` — returns all results across runs for the same image

**Files**:
- `frontend/src/pages/ResultsComparison.tsx`
- `frontend/src/components/ComparisonGrid.tsx`
- `frontend/src/components/TextDiff.tsx`
- `frontend/src/components/TitleDiff.tsx`
- `frontend/src/components/ConfidenceBar.tsx`
- `manga_ocr/api/routes/results.py` (updated with compare endpoints)

---

#### 3C — Manual Corrections & Catalog Management

**Capabilities**:
- Operator can override any extracted title/code
- Overrides stored as "ground truth" for evaluation
- Catalog search, filter, status management, CSV export

**Manual Corrections**:
- From results view: click "Edit" on any extraction, modify fields, save as ground truth
- Ground truth entries used in evaluation as additional gold standard data
- Correction history maintained (audit trail):
  ```
  corrections:
    id: UUID (PK)
    post_processing_result_id: UUID (FK)
    original_title_en: str | null
    original_title_ja: str | null
    original_code: str | null
    corrected_title_en: str | null
    corrected_title_ja: str | null
    corrected_code: str | null
    created_at: datetime (not null)
  ```

**Catalog Management UI**:
- Search: full-text search on title_en, title_ja, code
- Filters: status (auto_confirmed/needs_review/rejected), confidence range, date range
- Bulk actions: select multiple entries, change status
- Export: CSV download with all fields (title_en, title_ja, code, status, confidence, source_url, created_at)
- Entry detail: shows full extraction history (all models, all prompt versions that produced this entry)
- Inline edit: click any field to edit directly in the table

**Files**:
- `manga_ocr/db/crud.py` (updated: corrections table, bulk operations)
- `manga_ocr/api/routes/catalog.py` (updated: search, bulk, export)
- `manga_ocr/api/routes/results.py` (updated: override endpoint)
- `frontend/src/pages/Catalog.tsx` (updated)
- `frontend/src/components/CatalogSearch.tsx`
- `frontend/src/components/CatalogFilters.tsx`
- `frontend/src/components/CorrectionModal.tsx`

---

### Phase 3 Exclusions

- No Docker deployment (Phase 4)
- No WebSocket (Phase 4)
- No automated regression trigger on prompt change (manual trigger only)
- No model fine-tuning (use pre-trained models only)
- No automated A/B testing of prompt versions

---

## Phase 4: Production Deployment

**Status**: Future
**Prerequisite**: Phase 3 complete
**Delivers**: Docker Compose deployment, real-time updates, monitoring, error handling hardening

### Sub-Phases

#### 4A — Docker Compose

**Capabilities**:
- Single `docker-compose.yml` that brings up: API server, Dramatiq worker, Redis, PostgreSQL, React frontend (nginx)
- Environment-based configuration (no secrets in images)
- Volume mounts for image storage and model caches

**Services**:

```
docker-compose.yml services:
  api:
    build: .
    command: uvicorn manga_ocr.api.app:create_app --host 0.0.0.0 --port 8000
    ports: ["8000:8000"]
    depends_on: [db, redis]
    volumes:
      - ./configs.toml:/app/configs.toml:ro
      - ./ocrs.yaml:/app/ocrs.yaml:ro
      - image_data:/app/images
      - model_cache:/root/.cache/huggingface
    env_file: .env

  worker:
    build: .
    command: dramatiq manga_ocr.workers.ocr_worker
    depends_on: [db, redis]
    volumes:
      - ./configs.toml:/app/configs.toml:ro
      - ./ocrs.yaml:/app/ocrs.yaml:ro
      - image_data:/app/images
      - model_cache:/root/.cache/huggingface
    env_file: .env

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes:
      - redis_data:/data

  db:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    volumes:
      - pg_data:/var/lib/postgresql/data
    env_file: .env

  frontend:
    build: ./frontend
    ports: ["80:80"]
    depends_on: [api]

volumes:
  pg_data:
  redis_data:
  image_data:
  model_cache:
```

**Dockerfile** (Python backend + worker):
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen
COPY manga_ocr/ manga_ocr/
COPY prompts/ prompts/
COPY configs.toml ocrs.yaml main.py ./
```

**Dockerfile** (React frontend):
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY src/ src/
COPY public/ public/
COPY index.html vite.config.ts tsconfig.json ./
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

**Configuration**:
- `.env` file for secrets (API keys, DB password, Redis URL)
- `configs.toml` and `ocrs.yaml` mounted as read-only volumes
- HuggingFace model cache mounted as persistent volume
- Image storage mounted as persistent volume
- `.env.example` checked into git with placeholder values

**Files**:
- `Dockerfile`
- `docker-compose.yml`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `.env.example`
- `.dockerignore`

---

#### 4B — Real-Time Updates

**Capabilities**:
- WebSocket connection from frontend to backend
- Push pipeline status updates (pending -> processing -> completed/failed)
- Push new results as they arrive from each OCR model
- Eliminate polling

**WebSocket Protocol**:
- Client connects to `ws://host/ws/pipeline/{run_id}`
- Server pushes messages:
  ```json
  {"event": "status_change", "run_id": "...", "status": "processing"}
  {"event": "model_result", "run_id": "...", "model": "manga-ocr", "result": {...}}
  {"event": "extraction_complete", "run_id": "...", "extracted": {...}}
  {"event": "completed", "run_id": "...", "result": {...}}
  {"event": "error", "run_id": "...", "error": "..."}
  ```
- Client reconnects on disconnect with exponential backoff (1s, 2s, 4s, 8s, max 30s)

**Backend Implementation**:
- FastAPI WebSocket endpoint: `@app.websocket("/ws/pipeline/{run_id}")`
- Worker publishes updates to a Redis Pub/Sub channel after each pipeline stage
- WebSocket handler subscribes to the channel and forwards to client
- Connection management: track active connections, clean up on disconnect

**Files**:
- `manga_ocr/api/websocket.py`
- `manga_ocr/workers/ocr_worker.py` (updated: publish events to Redis Pub/Sub)
- `frontend/src/hooks/usePipelineWebSocket.ts`
- `frontend/src/components/PipelineDiagram.tsx` (updated: real-time status)

---

#### 4C — Monitoring & Error Handling

**Capabilities**:
- Structured logging (JSON format) to stdout
- Health check endpoint: `GET /health` — returns status of all dependencies
- Error tracking: all pipeline errors logged with context
- Retry queue visibility
- Metrics (optional): Prometheus endpoint

**Health Check** (`GET /health`):
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "openrouter": "ok",
    "models": {
      "manga-ocr": "available",
      "tesseract": "available",
      "paddle": "unavailable",
      "easyocr": "unavailable",
      "glm_ocr": "unavailable"
    }
  },
  "uptime_seconds": 3600
}
```

**Structured Logging**:
- Format: JSON lines to stdout
- Fields: timestamp, level, module, message, run_id (if applicable), model (if applicable), duration_ms (if applicable)
- Log levels: INFO for pipeline start/end, DEBUG for per-model details, WARNING for degraded service, ERROR for failures
- No sensitive data in logs (API keys redacted)

**Error Handling Hardening**:
- Request timeout middleware: 60s max for API requests
- Dramatiq dead-letter queue: permanently failed jobs viewable via API
- Image validation: max file size 20MB, allowed formats only (PNG, JPG, WEBP, TIFF, BMP)
- Graceful shutdown: SIGTERM handler completes in-progress jobs before stopping worker (30s grace period)
- Database connection pooling: pool_size=5, max_overflow=10, pool_timeout=30s
- Rate limiting on upload endpoint: max 10 uploads per minute

**Optional Metrics** (Prometheus):
- `manga_ocr_pipeline_total{status="completed|failed"}` — counter
- `manga_ocr_pipeline_duration_seconds{model="..."}` — histogram
- `manga_ocr_extraction_confidence{model="..."}` — histogram
- `manga_ocr_api_requests_total{endpoint="...", status="..."}` — counter
- Endpoint: `GET /metrics` (Prometheus format)

**Files**:
- `manga_ocr/api/health.py`
- `manga_ocr/api/middleware.py` (timeout, rate limiting, error handling)
- `manga_ocr/logging_config.py` (structured logging setup)
- `manga_ocr/api/metrics.py` (Prometheus metrics, optional)

---

### Phase 4 Exclusions

- No horizontal scaling (single VPS is sufficient for <50 posts/day)
- No CDN (self-hosted)
- No automated CI/CD pipeline (manual deploy)
- No SSL certificate automation (manual or Let's Encrypt standalone)
- No user management or multi-tenancy
- No automated backup strategy (manual pg_dump)

---

## Phase Dependency Graph

```
Phase 0 (OCR Engine)
    |
    v
Phase 1 (MVP Backend API)
    |
    v
Phase 2 (Multi-Model + Prompt Management)
    |
    v
Phase 3 (Evaluation & Comparison)
    |
    v
Phase 4 (Production Deployment)
```

Each phase builds strictly on the previous. No parallel phase development.

---

## User Story Numbering Convention

Each phase's user stories are prefixed for traceability:

| Phase | Prefix | Example |
|-------|--------|---------|
| Phase 0 | `US-O` | US-O1, US-O2, ..., US-O10 |
| Phase 1 | `US-1` | US-1A1 (sub-phase A), US-1B1 (sub-phase B), US-1C1 (sub-phase C), US-1D1 (sub-phase D) |
| Phase 2 | `US-2` | US-2A1 (models), US-2B1 (Agenta), US-2C1 (visualization), US-2D1 (URL input) |
| Phase 3 | `US-3` | US-3A1 (evaluation), US-3B1 (comparison), US-3C1 (catalog management) |
| Phase 4 | `US-4` | US-4A1 (Docker), US-4B1 (WebSocket), US-4C1 (monitoring) |

The letter after the phase number indicates the sub-phase (A, B, C, D, E). The final number is the story sequence within that sub-phase.
