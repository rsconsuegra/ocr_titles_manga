# V2 Plan: MVP Backend API

**Phase**: 1 (MVP Backend API)  
**Scope**: FastAPI server + PostgreSQL + Dramatiq/Redis task queue + minimal React frontend  
**Goal**: Persistent OCR pipeline with async job processing, result storage, and a web UI  
**Prerequisite**: Phase 0 (OCR Engine) — complete as `ocr_manga_title/` package

---

## What We Are Building

A FastAPI backend that wraps the Phase 0 OCR engine, adds:
1. PostgreSQL storage for pipeline runs, OCR results, extracted titles, and a catalog
2. Dramatiq + Redis async job queue for OCR pipeline execution
3. REST API for uploading images, triggering runs, browsing results, managing a catalog
4. Minimal React + TypeScript + Tailwind frontend for operators

## What We Are NOT Building (Yet)

- No Agenta.ai prompt management (Phase 2)
- No social media URL fetching (Phase 2)
- No evaluation / gold standard system (Phase 3)
- No WebSocket real-time updates (Phase 4)
- No Docker for the app itself (only PostgreSQL + Redis via docker-compose.dev.yml)
- No authentication
- No manga-ocr HuggingFace wrapper (dropped — glm_ocr stub stays)
- No `prompts/ocr/` directory (dropped)

---

## Target Directory Structure

```
manga_ocr/                              # Project root (unchanged)
  ocr_manga_title/                      # Python package (unchanged)
    __init__.py
    config.py
    schemas.py
    engine.py
    exceptions.py
    models/
      __init__.py
      base.py
      tesseract_model.py
      paddle_model.py
      easyocr_model.py
      glm_ocr_model.py
    preprocess/
      __init__.py
      base.py
      pipeline.py
      steps/
        __init__.py
        roi.py
        grayscale.py
        upscale.py
        denoise.py
        binarize.py
    postprocess/
      __init__.py
      llm_extractor.py
      rule_matcher.py
    db/                                 # NEW — database layer
      __init__.py
      session.py                        # Async engine + session factory
      models.py                         # SQLAlchemy ORM models (6 tables)
      crud.py                           # CRUD operations
    api/                                # NEW — FastAPI application
      __init__.py
      app.py                            # App factory, CORS, lifespan
      dependencies.py                   # DI: db session, config, engine
      schemas.py                        # Request/response Pydantic models
      routes/
        __init__.py
        inputs.py                       # Upload, get input status
        pipeline.py                     # Trigger, list, details
        results.py                      # List, override
        catalog.py                      # CRUD + export
        models.py                       # Model config endpoints
    workers/                            # NEW — task queue
      __init__.py
      broker.py                         # Redis + Dramatiq config
      ocr_worker.py                     # Dramatiq actor
  migrations/                           # NEW — Alembic
    env.py
    script.py.mako
    versions/
      001_initial.py
      002_seed_models.py
      003_seed_prompts.py
  prompts/
    llm/
      extract_title_v1.md               # Unchanged
  frontend/                             # NEW — React app
    package.json
    vite.config.ts
    tsconfig.json
    tailwind.config.js
    postcss.config.js
    index.html
    src/
      main.tsx
      App.tsx
      api/
        client.ts
      components/
        ImageUploader.tsx
        RunStatusBadge.tsx
        ConfidenceMeter.tsx
      pages/
        Dashboard.tsx
        Upload.tsx
        Runs.tsx
        RunDetail.tsx
        Catalog.tsx
  tests/
    __init__.py
    conftest.py                         # Updated
    test_config.py                      # Unchanged
    test_schemas.py                     # Unchanged
    test_models.py                      # Unchanged
    test_postprocess.py                 # Unchanged
    test_engine.py                      # Unchanged
    test_preprocess.py                  # Unchanged
    test_cli.py                         # Unchanged
    test_api/                           # NEW
      __init__.py
      conftest.py
      test_inputs.py
      test_pipeline.py
      test_results.py
      test_catalog.py
      test_models_route.py
    test_db/                            # NEW
      __init__.py
      conftest.py
      test_models.py
      test_crud.py
    test_worker/                        # NEW
      __init__.py
      conftest.py
      test_ocr_worker.py
  configs.toml                          # Updated (new fields)
  ocrs.yaml                             # Unchanged
  preprocess.yaml                       # Unchanged
  .env.example                          # NEW
  docker-compose.dev.yml                # NEW
  alembic.ini                           # NEW
  pyproject.toml                        # Updated (new deps)
  Makefile                              # Updated (new targets)
```

---

## Implementation Steps

### Step 1: Project Setup

**Task**: Update dependencies, create Docker dev services, add `.env.example`, update `configs.toml`.

**New dependencies** (add to `pyproject.toml`):
```
fastapi>=0.115
uvicorn[standard]
sqlalchemy[asyncio]>=2.0
asyncpg
alembic
dramatiq[redis]
python-multipart
httpx
```

**New dev dependencies**:
```
pytest-asyncio
aiosqlite
```

**`docker-compose.dev.yml`**:
```yaml
services:
  db:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: manga_ocr
      POSTGRES_USER: manga_ocr
      POSTGRES_PASSWORD: manga_ocr_dev
    volumes:
      - pg_data:/var/lib/postgresql/data
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
volumes:
  pg_data:
```

**`.env.example`**:
```
DATABASE_URL=postgresql+asyncpg://manga_ocr:manga_ocr_dev@localhost:5432/manga_ocr
REDIS_URL=redis://localhost:6379
OPENROUTER_API_KEY=sk-or-replace-me
OPENROUTER_DEFAULT_MODEL=google/gemini-2.5-flash
```

**`configs.toml` updates** — add:
```toml
images_path = "uploads/"

[openrouter]
api_key = "sk-or-replace-me"
default_model = "google/gemini-2.5-flash"
base_url = "https://openrouter.ai/api/v1"
```

**Files created/modified**:
- `docker-compose.dev.yml`
- `.env.example`
- `.gitignore` (add `.env`, `uploads/`, `__pycache__/`)
- `configs.toml`
- `pyproject.toml`

### Step 2: Database Session

**Task**: `ocr_manga_title/db/session.py` — async SQLAlchemy engine and session factory.

**Behavior**:
- Read `DATABASE_URL` from environment variable (fall back to sqlite for tests)
- Create `async_engine` with `create_async_engine(url, echo=False)`
- Create `async_session_factory` using `async_sessionmaker(engine, class_=AsyncSession)`
- Provide `get_db_session()` async generator for FastAPI dependency injection
- Provide `get_engine()` for direct engine access (workers, tests)
- Support both PostgreSQL (production) and aiosqlite (testing) via URL scheme detection

**Session Factory**:
```python
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Files created**:
- `ocr_manga_title/db/__init__.py`
- `ocr_manga_title/db/session.py`

### Step 3: Database Models

**Task**: `ocr_manga_title/db/models.py` — SQLAlchemy 2.0 ORM models for 6 tables.

**Tables**:

```python
class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    input_image_path: Mapped[str]
    source_url: Mapped[str | None]
    source_platform: Mapped[str | None]          # "twitter" | "facebook" | "manual"
    status: Mapped[str] = mapped_column(default="pending")  # pending|processing|completed|failed
    error_message: Mapped[str | None]
    preprocess_config: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    completed_at: Mapped[datetime | None]
    # relationships
    ocr_results: Mapped[list["OCRResult"]] = relationship(back_populates="pipeline_run", cascade="all, delete-orphan")
    catalog_entries: Mapped[list["CatalogEntry"]] = relationship(back_populates="source_run")

class OCRResult(Base):
    __tablename__ = "ocr_results"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipeline_runs.id"))
    model_name: Mapped[str]
    raw_text: Mapped[str]
    confidence: Mapped[float]
    processing_time_ms: Mapped[int]
    error: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    # relationships
    pipeline_run: Mapped["PipelineRun"] = relationship(back_populates="ocr_results")
    post_processing_results: Mapped[list["PostProcessingResult"]] = relationship(back_populates="ocr_result", cascade="all, delete-orphan")

class PostProcessingResult(Base):
    __tablename__ = "post_processing_results"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ocr_result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ocr_results.id"))
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("prompt_versions.id"))
    title_en: Mapped[str | None]
    title_ja: Mapped[str | None]
    code: Mapped[str | None]
    confidence: Mapped[float]
    processing_type: Mapped[str]       # "llm" | "rules" | "llm+rules"
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    # relationships
    ocr_result: Mapped["OCRResult"] = relationship(back_populates="post_processing_results")

class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    prompt_type: Mapped[str]           # "llm" (no "ocr" since prompts/ocr/ dropped)
    content: Mapped[str]
    version_number: Mapped[int]
    agenta_id: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=False)
    tags: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=func.now())

class CatalogEntry(Base):
    __tablename__ = "catalog_entries"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title_en: Mapped[str | None]
    title_ja: Mapped[str | None]
    code: Mapped[str | None]
    source_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipeline_runs.id"))
    confidence: Mapped[float]
    status: Mapped[str] = mapped_column(default="needs_review")  # auto_confirmed|needs_review|rejected
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime | None]
    # relationships
    source_run: Mapped["PipelineRun"] = relationship(back_populates="catalog_entries")

class ModelConfig(Base):
    __tablename__ = "model_configs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(unique=True)
    is_enabled: Mapped[bool] = mapped_column(default=True)
    parameters: Mapped[dict | None] = mapped_column(JSONB)
    language_hint: Mapped[str | None]
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
```

**Preprocessing data**: stored as JSONB on `pipeline_runs.preprocess_config` (config used) and returned in run details from the engine's `PreProcessResult`.

**Files created**:
- `ocr_manga_title/db/models.py`

### Step 4: Alembic Setup

**Task**: Configure Alembic, create 3 migrations.

**Alembic configuration** (`alembic.ini`):
- `sqlalchemy.url` left empty (set programmatically from env var in `migrations/env.py`)
- `script_location = migrations`

**`migrations/env.py`**:
- Import `Base.metadata` from `ocr_manga_title.db.models`
- Read `DATABASE_URL` from environment
- Use `run_async` for async migrations
- Target metadata = `Base.metadata`

**Migrations**:

1. **`001_initial.py`** — Create all 6 tables with proper types (UUID PKs, JSONB columns, foreign keys, indexes). Indexes on: `pipeline_runs.status`, `pipeline_runs.created_at`, `ocr_results.pipeline_run_id`, `catalog_entries.code`, `catalog_entries.status`, `model_configs.model_name`.

2. **`002_seed_models.py`** — Insert 4 rows into `model_configs`: tesseract (enabled), paddle (disabled), easyocr (disabled), glm_ocr (disabled). Parameters match `ocrs.yaml` defaults.

3. **`003_seed_prompts.py`** — Read `prompts/llm/extract_title_v1.md`, insert into `prompt_versions` as type "llm", version 1, `is_active=True`.

**Files created**:
- `alembic.ini`
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/001_initial.py`
- `migrations/versions/002_seed_models.py`
- `migrations/versions/003_seed_prompts.py`

### Step 5: CRUD Operations

**Task**: `ocr_manga_title/db/crud.py` — typed CRUD functions for all entities.

**Operations**:

```python
# PipelineRun
async def create_pipeline_run(session, input_image_path, source_url=None, source_platform="manual", preprocess_config=None) -> PipelineRun
async def get_pipeline_run(session, run_id: UUID) -> PipelineRun | None
async def list_pipeline_runs(session, status: str | None = None, limit: int = 20, offset: int = 0) -> list[PipelineRun]
async def update_pipeline_run_status(session, run_id: UUID, status: str, error_message: str | None = None) -> PipelineRun | None

# OCRResult
async def create_ocr_result(session, pipeline_run_id: UUID, model_name: str, raw_text: str, confidence: float, processing_time_ms: int, error: str | None = None) -> OCRResult
async def get_ocr_results_for_run(session, pipeline_run_id: UUID) -> list[OCRResult]

# PostProcessingResult
async def create_post_processing_result(session, ocr_result_id: UUID, title_en, title_ja, code, confidence, processing_type, prompt_version_id=None) -> PostProcessingResult
async def get_post_processing_results(session, ocr_result_id: UUID) -> list[PostProcessingResult]

# PromptVersion
async def get_active_prompt(session, prompt_type: str) -> PromptVersion | None
async def list_prompts(session, prompt_type: str | None = None) -> list[PromptVersion]

# CatalogEntry
async def create_catalog_entry(session, source_run_id: UUID, title_en, title_ja, code, confidence) -> CatalogEntry
async def get_catalog_entry(session, entry_id: UUID) -> CatalogEntry | None
async def list_catalog_entries(session, status: str | None = None, search: str | None = None, limit: int = 20, offset: int = 0) -> list[CatalogEntry]
async def update_catalog_entry(session, entry_id: UUID, **kwargs) -> CatalogEntry | None
async def count_catalog_entries(session, status: str | None = None) -> int

# ModelConfig
async def list_model_configs(session) -> list[ModelConfig]
async def get_model_config(session, model_name: str) -> ModelConfig | None
async def update_model_config(session, model_name: str, **kwargs) -> ModelConfig | None
```

All functions use async SQLAlchemy queries with proper type hints. No raw SQL.

**Files created**:
- `ocr_manga_title/db/crud.py`

### Step 6: FastAPI App Factory

**Task**: `ocr_manga_title/api/app.py` — create FastAPI application with lifespan, CORS, routers.

**App Factory**:
```python
def create_app() -> FastAPI:
    app = FastAPI(
        title="Manga OCR API",
        version="0.2.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    # CORS for frontend dev
    app.add_middleware(CORALSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
    # Lifespan: optionally warm up models, close engine on shutdown
    app.include_router(inputs_router, prefix="/api/v1/inputs", tags=["inputs"])
    app.include_router(pipeline_router, prefix="/api/v1/pipeline", tags=["pipeline"])
    app.include_router(results_router, prefix="/api/v1/results", tags=["results"])
    app.include_router(catalog_router, prefix="/api/v1/catalog", tags=["catalog"])
    app.include_router(models_router, prefix="/api/v1/models", tags=["models"])
    return app
```

**Error handling**: global exception handler that catches unhandled errors, logs them, returns `{"detail": "...", "error_code": "internal_error"}` with 500 status.

**Files created**:
- `ocr_manga_title/api/__init__.py`
- `ocr_manga_title/api/app.py`

### Step 7: API Schemas

**Task**: `ocr_manga_title/api/schemas.py` — request/response Pydantic models for all endpoints.

**Request Models**:
```python
class PipelineTriggerRequest(BaseModel):
    preprocess_enabled: bool = True

class ResultOverrideRequest(BaseModel):
    title_en: str | None = None
    title_ja: str | None = None
    code: str | None = None

class CatalogUpdateRequest(BaseModel):
    status: str | None = None          # auto_confirmed|needs_review|rejected
    title_en: str | None = None
    title_ja: str | None = None
    code: str | None = None

class ModelConfigUpdateRequest(BaseModel):
    is_enabled: bool | None = None
    parameters: dict | None = None
    language_hint: str | None = None
```

**Response Models**:
```python
class PipelineRunResponse(BaseModel):
    id: UUID
    input_image_path: str
    status: str
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

class PipelineRunDetailResponse(PipelineRunResponse):
    ocr_results: list["OCRResultResponse"]
    post_processing_results: list["PostProcessingResultResponse"]

class OCRResultResponse(BaseModel):
    id: UUID
    model_name: str
    raw_text: str
    confidence: float
    processing_time_ms: int
    error: str | None
    created_at: datetime

class PostProcessingResultResponse(BaseModel):
    id: UUID
    title_en: str | None
    title_ja: str | None
    code: str | None
    confidence: float
    processing_type: str
    created_at: datetime

class CatalogEntryResponse(BaseModel):
    id: UUID
    title_en: str | None
    title_ja: str | None
    code: str | None
    source_run_id: UUID
    confidence: float
    status: str
    created_at: datetime
    updated_at: datetime | None

class ModelConfigResponse(BaseModel):
    model_name: str
    is_enabled: bool
    parameters: dict | None
    language_hint: str | None
    updated_at: datetime

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
```

**Files created**:
- `ocr_manga_title/api/schemas.py`

### Step 8: API Dependencies

**Task**: `ocr_manga_title/api/dependencies.py` — FastAPI dependency injection.

**Dependencies**:
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Yields async db session from session factory
    ...

def get_config() -> AppConfig:
    # Loads configs.toml + ocrs.yaml + preprocess.yaml
    ...

def get_ocr_engine(config: AppConfig = Depends(get_config)) -> OCREngine:
    # Creates or returns cached OCREngine instance
    ...
```

**Files created**:
- `ocr_manga_title/api/dependencies.py`
- `ocr_manga_title/api/routes/__init__.py`

### Step 9: Input Routes

**Task**: `ocr_manga_title/api/routes/inputs.py` — upload and get status.

**Endpoints**:

`POST /api/v1/inputs/upload`:
- Accept multipart form with 1-10 image files
- Validate: file extension (PNG, JPG, WEBP, TIFF, BMP), max 20MB per file
- Save to `uploads/` directory with UUID filename, preserve extension
- Create `pipeline_runs` row per image with status="pending", source_platform="manual"
- Return list of created `PipelineRunResponse`

`GET /api/v1/inputs/{run_id}`:
- Return `PipelineRunResponse` for the given run_id
- 404 if not found

**Files created**:
- `ocr_manga_title/api/routes/inputs.py`

### Step 10: Pipeline Routes

**Task**: `ocr_manga_title/api/routes/pipeline.py` — trigger, list, details.

**Endpoints**:

`POST /api/v1/pipeline/run/{run_id}`:
- Validate run exists and status is "pending"
- Update status to "pending" (idempotent)
- Enqueue Dramatiq message with `run_id`
- Return `{"message": "Pipeline run enqueued", "run_id": "..."}`

`GET /api/v1/pipeline/runs`:
- Query params: `status`, `limit` (default 20, max 100), `offset` (default 0)
- Return `PaginatedResponse[PipelineRunResponse]`

`GET /api/v1/pipeline/runs/{run_id}`:
- Return `PipelineRunDetailResponse` with all OCR results and post-processing results
- 404 if not found

**Files created**:
- `ocr_manga_title/api/routes/pipeline.py`

### Step 11: Results + Catalog Routes

**Task**: Results override + full catalog CRUD.

**Results Endpoints** (`ocr_manga_title/api/routes/results.py`):

`GET /api/v1/results`:
- Query params: `model_name`, `min_confidence`, `max_confidence`, `limit`, `offset`
- Return `PaginatedResponse[PostProcessingResultResponse]`

`PUT /api/v1/results/{result_id}/override`:
- Accept `ResultOverrideRequest` body
- Update the `PostProcessingResult` fields
- If linked `CatalogEntry` exists, update its fields too, mark status as "needs_review"
- Return updated `PostProcessingResultResponse`

**Catalog Endpoints** (`ocr_manga_title/api/routes/catalog.py`):

`GET /api/v1/catalog`:
- Query params: `status`, `search` (searches title_en, title_ja, code), `limit`, `offset`
- Return `PaginatedResponse[CatalogEntryResponse]`

`GET /api/v1/catalog/{entry_id}`:
- Return `CatalogEntryResponse`
- 404 if not found

`PUT /api/v1/catalog/{entry_id}`:
- Accept `CatalogUpdateRequest` body
- Update status, title_en, title_ja, code as provided
- Set `updated_at` to now
- Return updated `CatalogEntryResponse`

`GET /api/v1/catalog/export`:
- Query all catalog entries (no pagination limit)
- Return CSV file download with columns: id, title_en, title_ja, code, status, confidence, source_run_id, created_at, updated_at
- Content-Type: text/csv, Content-Disposition: attachment

**Files created**:
- `ocr_manga_title/api/routes/results.py`
- `ocr_manga_title/api/routes/catalog.py`

### Step 12: Model Config Routes

**Task**: `ocr_manga_title/api/routes/models.py` — list and update model configs.

**Endpoints**:

`GET /api/v1/models`:
- Return list of `ModelConfigResponse` from database

`PUT /api/v1/models/{model_name}`:
- Accept `ModelConfigUpdateRequest` body
- Validate `model_name` exists in database
- Update provided fields, set `updated_at` to now
- Return updated `ModelConfigResponse`
- 404 if model_name not found

**Files created**:
- `ocr_manga_title/api/routes/models.py`

### Step 13: Worker Broker

**Task**: `ocr_manga_title/workers/broker.py` — configure Dramatiq with Redis.

**Behavior**:
- Read `REDIS_URL` from environment (default `redis://localhost:6379`)
- Create `dramatiq.brokers.redis.RedisBroker`
- Set as default Dramatiq broker
- Configure: `heartbeat_timeout=60000` (60s for long OCR jobs), `queue_name="manga_ocr"`

**Files created**:
- `ocr_manga_title/workers/__init__.py`
- `ocr_manga_title/workers/broker.py`

### Step 14: OCR Worker

**Task**: `ocr_manga_title/workers/ocr_worker.py` — Dramatiq actor that runs the pipeline.

**Actor**:
```python
@dramatiq.actor(
    max_retries=3,
    min_backoff=10000,    # 10s
    max_backoff=60000,    # 60s
    time_limit=300000,    # 5 min hard limit
)
async def process_pipeline_run(run_id: str):
    ...
```

**Job Flow**:
1. Create async DB session
2. Fetch `PipelineRun` by `run_id`
3. Update status to "processing"
4. Load enabled model configs from DB, build `ModelConfig` dict for `OCREngine`
5. Load active prompt from `prompt_versions` (fallback to file)
6. Call `OCREngine.process(image_path)`
7. For each `OCRResult`: store in `ocr_results` table
8. For each `PostProcessingResult`: store in `post_processing_results` table
9. If extracted title is not None: create `CatalogEntry`
10. Update `pipeline_runs` status to "completed", set `completed_at`
11. On error: set status to "failed", store `error_message`

**Retry Policy**:
- LLM API errors (5xx, timeout): retry up to 3 times
- OCR model errors: do NOT retry (captured in OCRResult)
- Database connection errors: retry up to 3 times
- Image file not found: do NOT retry (permanent error)

**Worker Sync Wrapper**: Since Dramatiq actors are synchronous but `OCREngine` is async, use `asyncio.run()` or an event loop wrapper to bridge sync/async.

**Files created**:
- `ocr_manga_title/workers/ocr_worker.py`

### Step 15: Frontend Setup

**Task**: Initialize Vite + React + TypeScript + Tailwind in `frontend/`.

**Tech Stack**:
- Vite 6
- React 19 + TypeScript 5
- Tailwind CSS 4
- No state management library (useState + fetch)
- React Router for page navigation

**`package.json` dependencies**:
```
react, react-dom, react-router-dom
```

**`package.json` dev dependencies**:
```
typescript, @types/react, @types/react-dom
vite, @vitejs/plugin-react
tailwindcss, @tailwindcss/vite
```

**`vite.config.ts`**:
- Proxy `/api` to `http://localhost:8000` during development

**Pages/routes**:
- `/` — Dashboard (recent runs, quick stats)
- `/upload` — Upload form
- `/runs` — Pipeline run history
- `/runs/:id` — Run detail
- `/catalog` — Catalog entries

**Files created**:
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/tsconfig.json`
- `frontend/tailwind.config.js`
- `frontend/postcss.config.js`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`

### Step 16: Frontend API Client + Shared Components

**Task**: HTTP client and reusable UI components.

**API Client** (`frontend/src/api/client.ts`):
- Base fetch wrapper with error handling
- Typed functions for each API endpoint
- Base URL from env or default `http://localhost:8000`

**Components**:
- `ImageUploader` — drag-and-drop + file picker, shows preview thumbnails, validates file types, 1-10 files
- `RunStatusBadge` — colored badge: pending (gray), processing (blue), completed (green), failed (red)
- `ConfidenceMeter` — horizontal bar, color-coded: red (<0.3), yellow (0.3-0.7), green (>0.7)

**Files created**:
- `frontend/src/api/client.ts`
- `frontend/src/components/ImageUploader.tsx`
- `frontend/src/components/RunStatusBadge.tsx`
- `frontend/src/components/ConfidenceMeter.tsx`

### Step 17: Frontend Pages

**Task**: All 5 pages with full functionality.

**Dashboard** (`frontend/src/pages/Dashboard.tsx`):
- Quick stats: total runs, completed, failed, success rate
- Recent 5 pipeline runs table with status badges
- Link to upload page

**Upload** (`frontend/src/pages/Upload.tsx`):
- `ImageUploader` component
- Submit button triggers `POST /api/v1/inputs/upload`
- After upload: show created runs with "Trigger Pipeline" buttons
- Trigger calls `POST /api/v1/pipeline/run/{run_id}`

**Runs** (`frontend/src/pages/Runs.tsx`):
- Table: run ID (truncated), image path, status badge, created_at, completed_at
- Pagination controls
- Status filter dropdown
- Click row to navigate to run detail

**RunDetail** (`frontend/src/pages/RunDetail.tsx`):
- Input image preview
- Status badge and timestamps
- Per-model OCR results: raw_text, confidence meter, processing time
- Post-processing results: extracted title_en, title_ja, code with confidence
- Manual override form (PUT /api/v1/results/{id}/override)

**Catalog** (`frontend/src/pages/Catalog.tsx`):
- Table: title_en, title_ja, code, confidence meter, status badge, created_at
- Search input (searches title and code)
- Status filter
- Pagination
- Click row to expand: source run link, edit fields, update status
- Export CSV button

**Files created**:
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/Upload.tsx`
- `frontend/src/pages/Runs.tsx`
- `frontend/src/pages/RunDetail.tsx`
- `frontend/src/pages/Catalog.tsx`

### Step 18: Tests

**Task**: Tests for API routes, database CRUD, and worker logic.

**Test Fixtures** (`tests/test_api/conftest.py`):
- `async_client`: httpx `AsyncClient` with FastAPI app, using aiosqlite in-memory database
- `db_session`: async session for the test database
- Tables created/dropped per test via `Base.metadata.create_all` / `drop_all`

**API Route Tests** (`tests/test_api/`):
- `test_inputs.py`: upload valid image, upload invalid format, upload too many files, get run status, get nonexistent run
- `test_pipeline.py`: trigger run, trigger nonexistent run, list runs, list runs filtered, get run details, get run details with results
- `test_results.py`: list results, override result, override nonexistent result
- `test_catalog.py`: list entries, search entries, filter by status, get entry, update entry status, export CSV, update nonexistent
- `test_models_route.py`: list models, update model enable/disable, update nonexistent model

**Database Tests** (`tests/test_db/`):
- `test_models.py`: create/read all 6 entity types, relationship integrity, cascade deletes
- `test_crud.py`: all CRUD functions, pagination, filtering, search

**Worker Tests** (`tests/test_worker/`):
- `test_ocr_worker.py`: successful pipeline run (mocked engine), engine failure, missing run, status transitions

**All tests**: use mocked OCREngine (no real OCR calls), mocked LLM (no real API calls), in-memory SQLite (no real PostgreSQL).

**Files created**:
- `tests/test_api/__init__.py`
- `tests/test_api/conftest.py`
- `tests/test_api/test_inputs.py`
- `tests/test_api/test_pipeline.py`
- `tests/test_api/test_results.py`
- `tests/test_api/test_catalog.py`
- `tests/test_api/test_models_route.py`
- `tests/test_db/__init__.py`
- `tests/test_db/conftest.py`
- `tests/test_db/test_models.py`
- `tests/test_db/test_crud.py`
- `tests/test_worker/__init__.py`
- `tests/test_worker/conftest.py`
- `tests/test_worker/test_ocr_worker.py`

### Step 19: Configuration + Makefile Updates

**Task**: Update Makefile with new targets, ensure all configuration is consistent.

**New Makefile targets**:
```makefile
dev:          # Start docker-compose.dev.yml (PostgreSQL + Redis) in background
dev-down:     # Stop docker-compose.dev.yml
migrate:      # Run alembic upgrade head
migrate-create: # Create a new alembic migration (usage: make migrate-create msg="description")
api:          # Start uvicorn server
worker:       # Start dramatiq worker
frontend:     # Start vite dev server (cd frontend && npm run dev)
setup-db:     # dev + migrate (one command to get DB ready)
test-all:     # Run all tests including new test directories
```

**Existing targets updated**:
- `test`: run pytest with `--tb=short`
- `lint`: run ruff check + format check (unchanged)
- `setup`: `uv sync` (unchanged)

**Files modified**:
- `Makefile`

---

## Configuration Files

### `configs.toml` (updated)

```toml
images_path = "uploads/"

[openrouter]
api_key = "sk-or-replace-me"
default_model = "google/gemini-2.5-flash"
base_url = "https://openrouter.ai/api/v1"
```

### `.env.example`

```
DATABASE_URL=postgresql+asyncpg://manga_ocr:manga_ocr_dev@localhost:5432/manga_ocr
REDIS_URL=redis://localhost:6379
OPENROUTER_API_KEY=sk-or-replace-me
OPENROUTER_DEFAULT_MODEL=google/gemini-2.5-flash
```

### `docker-compose.dev.yml`

```yaml
services:
  db:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: manga_ocr
      POSTGRES_USER: manga_ocr
      POSTGRES_PASSWORD: manga_ocr_dev
    volumes:
      - pg_data:/var/lib/postgresql/data
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
volumes:
  pg_data:
```

---

## API Endpoint Summary

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/inputs/upload` | Upload 1-10 images, create pending runs |
| GET | `/api/v1/inputs/{run_id}` | Get run status |
| POST | `/api/v1/pipeline/run/{run_id}` | Trigger pipeline for a run |
| GET | `/api/v1/pipeline/runs` | List runs (paginated, filterable) |
| GET | `/api/v1/pipeline/runs/{run_id}` | Full run details with results |
| GET | `/api/v1/results` | List post-processing results |
| PUT | `/api/v1/results/{result_id}/override` | Manual correction |
| GET | `/api/v1/catalog` | List catalog entries (searchable) |
| GET | `/api/v1/catalog/{entry_id}` | Get catalog entry |
| PUT | `/api/v1/catalog/{entry_id}` | Update catalog entry |
| GET | `/api/v1/catalog/export` | Export catalog as CSV |
| GET | `/api/v1/models` | List model configs |
| PUT | `/api/v1/models/{model_name}` | Update model config |

---

## Acceptance Criteria for V2

- [ ] `docker-compose -f docker-compose.dev.yml up -d` starts PostgreSQL and Redis
- [ ] `make migrate` creates all tables and seeds data
- [ ] FastAPI app starts with `make api` and serves OpenAPI docs at `/api/docs`
- [ ] `POST /api/v1/inputs/upload` accepts images and creates pending pipeline runs
- [ ] `POST /api/v1/pipeline/run/{run_id}` enqueues an OCR job
- [ ] Dramatiq worker processes the job end-to-end: OCR -> LLM -> rules -> store results
- [ ] `GET /api/v1/pipeline/runs/{run_id}` returns full details including OCR results and extracted titles
- [ ] `GET /api/v1/catalog` lists catalog entries from completed runs
- [ ] `PUT /api/v1/catalog/{entry_id}` updates entry status
- [ ] `GET /api/v1/catalog/export` downloads CSV
- [ ] `GET /api/v1/models` lists all 4 model configs
- [ ] `PUT /api/v1/models/{model_name}` enables/disables a model
- [ ] Frontend loads at `http://localhost:5173` with all 5 pages
- [ ] Upload page accepts images and triggers pipeline
- [ ] Runs page lists pipeline runs with status badges
- [ ] Run detail page shows OCR results and extracted data
- [ ] Catalog page shows entries with search and filter
- [ ] All tests pass (`make test-all`)
- [ ] No lint errors (`make lint`)

---

## Phase 0 Status (Pre-existing)

The following Phase 0 items are complete and unchanged:
- `ocr_manga_title/` package: config, schemas, engine, exceptions, models, preprocess, postprocess
- 177 tests passing
- Existing test files unchanged
- `prompts/llm/extract_title_v1.md` unchanged

The following Phase 0 gaps are explicitly excluded from V2:
- `manga_ocr_model.py` (HuggingFace manga-ocr) — dropped, glm_ocr stub stays
- `prompts/ocr/` directory — dropped
