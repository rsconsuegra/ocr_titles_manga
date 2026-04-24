# Database Reference

## Schema Diagram

```
┌──────────────────┐       ┌──────────────────────┐       ┌─────────────────────────┐
│   pipeline_      │       │      ocr_results      │       │ post_processing_results  │
│     profiles     │       │                       │       │                          │
├──────────────────┤       ├──────────────────────┤       ├──────────────────────────┤
│ id (PK, UUID)    │       │ id (PK, UUID)        │       │ id (PK, UUID)            │
│ name (UNIQUE)    │       │ pipeline_run_id (FK) │──────►│ ocr_result_id (FK)       │
│ description      │       │ model_name           │       │ prompt_version_id (FK)   │──┐
│ preprocess_steps │       │ raw_text             │       │ title_en                 │  │
│ ocr_models       │       │ confidence           │       │ title_ja                 │  │
│ enable_llm       │       │ processing_time_ms   │       │ code                     │  │
│ is_default       │       │ error                │       │ confidence               │  │
│ created_at       │       │ created_at           │       │ processing_type          │  │
│ updated_at       │       └──────────────────────┘       │ created_at               │  │
└──────────────────┘                                      └──────────────────────────┘  │
                                                                                         │
┌──────────────────┐       ┌──────────────────────┐       ┌─────────────────────────┐  │
│   batch_runs     │       │   pipeline_runs       │       │    prompt_versions      │  │
├──────────────────┤       ├──────────────────────┤       ├─────────────────────────┤  │
│ id (PK, UUID)    │◄──┐   │ id (PK, UUID)        │       │ id (PK, UUID)           │  │
│ name             │   │   │ input_image_path     │       │ prompt_type             │  │
│ status           │   │   │ source_url           │       │ content                 │  │
│ total_count      │   │   │ source_platform      │       │ version_number          │  │
│ completed_count  │   └───│ batch_run_id (FK)    │       │ agenta_id               │  │
│ failed_count     │       │ status               │       │ is_active               │  │
│ created_at       │       │ error_message        │       │ tags                    │  │
│ completed_at     │       │ preprocess_config    │◄──────│ created_at              │  │
└──────────────────┘       │ created_at           │ snap- └─────────────────────────┘  │
                           │ completed_at         │ shot                              │
                           └──────────┬───────────┘                                   │
                                      │                                               │
                                      │ source_run_id (FK)                            │
                                      ▼                                               │
                           ┌──────────────────────┐                                   │
                           │   catalog_entries     │                                   │
                           ├──────────────────────┤                                   │
                           │ id (PK, UUID)        │                                   │
                           │ title_en             │                                   │
                           │ title_ja             │                                   │
                           │ code                 │                                   │
                           │ source_run_id (FK)   │                                   │
                           │ confidence           │                                   │
                           │ status               │                                   │
                           │ created_at           │                                   │
                           │ updated_at           │                                   │
                           └──────────────────────┘                                   │
                                                                                      │
┌──────────────────┐                                                                  │
│   model_configs  │                                                                  │
├──────────────────┤       (PromptVersion referenced by
│ id (PK, UUID)    │        PostProcessingResult.prompt_version_id)
│ model_name (UQ)  │
│ is_enabled       │
│ parameters (JSON)│
│ language_hint    │
│ updated_at       │
└──────────────────┘
```

---

## ORM Models

All models inherit from `Base(DeclarativeBase)` in `db/models.py`.

### `PipelineProfile`

Stores named, reusable pipeline configurations.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | PK | `uuid4()` | |
| `name` | String(200) | **UNIQUE, NOT NULL** | | Human-readable identifier |
| `description` | String(500) | nullable | | Optional description |
| `preprocess_steps` | JSON | nullable | | `{step_name: {param: value, ...}, ...}` |
| `ocr_models` | JSON | nullable | | `{model_name: {param: value, ...}, ...}` |
| `enable_llm` | Boolean | NOT NULL | `False` | |
| `is_default` | Boolean | NOT NULL | `False` | At most one should be True |
| `created_at` | DateTime | NOT NULL | `now()` | Server default |
| `updated_at` | DateTime | nullable | `now()` | Auto-updates on change |

**Index**: `ix_pipeline_profiles_is_default` on `is_default`

### `BatchRun`

Groups multiple `PipelineRun` records for bulk processing.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | PK | `uuid4()` | |
| `name` | String(200) | nullable | | Optional human-readable name |
| `status` | String(20) | NOT NULL | `"pending"` | `pending`, `processing`, `completed`, `partial_failure`, `failed` |
| `total_count` | Integer | NOT NULL | | Set at creation |
| `completed_count` | Integer | NOT NULL | `0` | Updated by `update_batch_progress()` |
| `failed_count` | Integer | NOT NULL | `0` | Updated by `update_batch_progress()` |
| `created_at` | DateTime | NOT NULL | `now()` | |
| `completed_at` | DateTime | nullable | | Set when all runs finish |

**Relationships**: `runs → list[PipelineRun]` (back_populates)

### `PipelineRun`

Tracks a single image through the pipeline.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | PK | `uuid4()` | |
| `input_image_path` | String(500) | NOT NULL | | Path to uploaded image on disk |
| `source_url` | String(1000) | nullable | | Original URL if scraped |
| `source_platform` | String(50) | nullable | | e.g. `"manual"` |
| `status` | String(20) | NOT NULL | `"pending"` | `pending`, `processing`, `completed`, `failed` |
| `error_message` | Text | nullable | | Set on failure |
| `preprocess_config` | JSON | nullable | | Config snapshot from profile (or null for legacy) |
| `batch_run_id` | UUID FK → `batch_runs.id` | nullable | | Set when part of a batch |
| `created_at` | DateTime | NOT NULL | `now()` | |
| `completed_at` | DateTime | nullable | | Set on completion/failure |

**Relationships**:
- `ocr_results → list[OCRResult]` (cascade delete)
- `catalog_entries → list[CatalogEntry]`
- `batch_run → BatchRun | None`

**Indexes**: `status`, `created_at`, `batch_run_id`

### `OCRResult`

Raw OCR output from a single model within a pipeline run.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | PK | `uuid4()` | |
| `pipeline_run_id` | UUID FK → `pipeline_runs.id` | NOT NULL | CASCADE delete | |
| `model_name` | String(50) | NOT NULL | | e.g. `"tesseract"` |
| `raw_text` | Text | NOT NULL | | OCR output text |
| `confidence` | Float | NOT NULL | | 0.0–1.0 |
| `processing_time_ms` | Integer | NOT NULL | | |
| `error` | Text | nullable | | Error message if model failed |
| `created_at` | DateTime | NOT NULL | `now()` | |

**Relationships**: `post_processing_results → list[PostProcessingResult]` (cascade delete)

### `PostProcessingResult`

LLM or rule-extracted title metadata.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | PK | `uuid4()` | |
| `ocr_result_id` | UUID FK → `ocr_results.id` | NOT NULL | CASCADE delete | |
| `prompt_version_id` | UUID FK → `prompt_versions.id` | nullable | | |
| `title_en` | String(500) | nullable | | English title |
| `title_ja` | String(500) | nullable | | Japanese title |
| `code` | String(50) | nullable | | ISBN code |
| `confidence` | Float | NOT NULL | | 0.0–1.0 |
| `processing_type` | String(20) | NOT NULL | | `"llm"`, `"rules"`, `"llm+rules"`, `"unknown"` |
| `created_at` | DateTime | NOT NULL | `now()` | |

### `CatalogEntry`

Deduplicated manga title in the master catalog.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | PK | `uuid4()` | |
| `title_en` | String(500) | nullable | | |
| `title_ja` | String(500) | nullable | | |
| `code` | String(50) | nullable | | ISBN |
| `source_run_id` | UUID FK → `pipeline_runs.id` | NOT NULL | | |
| `confidence` | Float | NOT NULL | | |
| `status` | String(20) | NOT NULL | `"needs_review"` | `needs_review`, `auto_confirmed`, `rejected` |
| `created_at` | DateTime | NOT NULL | `now()` | |
| `updated_at` | DateTime | nullable | | |

**Indexes**: `code`, `status`

### `PromptVersion`

Versioned prompt template for LLM extraction.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | PK | `uuid4()` | |
| `prompt_type` | String(20) | NOT NULL | | e.g. `"llm"` |
| `content` | Text | NOT NULL | | The prompt text |
| `version_number` | Integer | NOT NULL | | |
| `agenta_id` | String(100) | nullable | | External ID for Agenta integration |
| `is_active` | Boolean | NOT NULL | `False` | At most one active per type |
| `tags` | String(500) | nullable | | |
| `created_at` | DateTime | NOT NULL | `now()` | |

### `ModelConfig`

Per-OCR-model runtime configuration (persisted, mutable at runtime).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | PK | `uuid4()` | |
| `model_name` | String(50) | **UNIQUE, NOT NULL** | | Must match `MODEL_REGISTRY` key |
| `is_enabled` | Boolean | NOT NULL | `True` | |
| `parameters` | JSON | nullable | | Model-specific params |
| `language_hint` | String(50) | nullable | | Default language |
| `updated_at` | DateTime | NOT NULL | `now()` | Auto-updates |

---

## CRUD Functions (`db/crud.py`)

### Pipeline Run

| Function | Signature | Returns |
|---|---|---|
| `create_pipeline_run` | `(session, **kwargs)` | `PipelineRun` |
| `get_pipeline_run` | `(session, run_id)` | `PipelineRun \| None` |
| `list_pipeline_runs` | `(session, status?, limit, offset)` | `list[PipelineRun]` |
| `count_pipeline_runs` | `(session, status?)` | `int` |
| `get_pipeline_run_detail` | `(session, run_id)` | `dict \| None` (eager-loaded with OCR + post-processing) |

### Batch Run

| Function | Signature | Returns |
|---|---|---|
| `create_batch_run` | `(session, *, name, total_count)` | `BatchRun` |
| `get_batch_run` | `(session, batch_id)` | `BatchRun \| None` |
| `list_batch_runs` | `(session, status?, limit, offset)` | `list[BatchRun]` |
| `count_batch_runs` | `(session, status?)` | `int` |
| `update_batch_run` | `(session, batch_id, **kwargs)` | `BatchRun \| None` |
| `update_batch_progress` | `(session, batch_id)` | `BatchRun \| None` — counts completed/failed children, sets final status |

### Profile

| Function | Signature | Returns |
|---|---|---|
| `create_profile` | `(session, *, name, description?, ...)` | `PipelineProfile` |
| `get_profile` | `(session, profile_id)` | `PipelineProfile \| None` |
| `get_default_profile` | `(session)` | `PipelineProfile \| None` |
| `list_profiles` | `(session, limit, offset)` | `list[PipelineProfile]` |
| `count_profiles` | `(session)` | `int` |
| `update_profile` | `(session, profile_id, **kwargs)` | `PipelineProfile \| None` |
| `delete_profile` | `(session, profile_id)` | `bool` |
| `_unset_default_profiles` | `(session)` | `None` (internal) |

### Catalog

| Function | Signature | Returns |
|---|---|---|
| `get_catalog_entry` | `(session, entry_id)` | `CatalogEntry \| None` |
| `list_catalog_entries` | `(session, status?, limit, offset)` | `list[CatalogEntry]` |
| `count_catalog_entries` | `(session, status?)` | `int` |
| `update_catalog_entry` | `(session, entry_id, **kwargs)` | `CatalogEntry \| None` |
| `get_catalog_entry_by_run` | `(session, run_id)` | `CatalogEntry \| None` |

### Model Config

| Function | Signature | Returns |
|---|---|---|
| `get_model_config` | `(session, model_name)` | `ModelConfig \| None` |
| `list_model_configs` | `(session, enabled_only?)` | `list[ModelConfig]` |
| `update_model_config` | `(session, model_name, **kwargs)` | `ModelConfig \| None` |

### Prompts

| Function | Signature | Returns |
|---|---|---|
| `get_active_prompt` | `(session, prompt_type)` | `PromptVersion \| None` |
| `list_prompts` | `(session, prompt_type?)` | `list[PromptVersion]` |

---

## Migrations

Managed by Alembic. Config in `alembic.ini`, env in `migrations/env.py`.

### Migration Chain

| Version | File | Description |
|---|---|---|
| 001 | `001_initial.py` | Creates all initial tables (pipeline_runs, ocr_results, post_processing_results, prompt_versions, catalog_entries, model_configs) |
| 002 | `002_seed_models.py` | Seeds `model_configs` with 4 models (tesseract, paddle, easyocr, glm_ocr) |
| 003 | `003_seed_prompts.py` | Seeds `prompt_versions` with initial LLM extraction prompt |
| 004 | `004_add_batch_run.py` | Creates `batch_runs` table + adds `batch_run_id` FK to `pipeline_runs` |
| 005 | `005_add_pipeline_profile.py` | Creates `pipeline_profiles` table + index on `is_default` |

### Running Migrations

```bash
# Apply all pending
make migrate
# or
uv run alembic upgrade head

# Rollback one
make migrate-down
# or
uv run alembic downgrade -1

# Create new (autogenerate)
make migrate-create msg="description"
```

---

## Session Management

### API Sessions (`db/session.py`)

A shared async engine is created at module import time:

```python
engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=10)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
```

The `get_db()` dependency in `api/dependencies.py` yields a session with auto-commit/rollback.

### Worker Sessions (`workers/ocr_worker.py`)

The worker creates a **new engine per invocation** to avoid event-loop reuse bugs:

```python
def _run_async(coro):
    loop = asyncio.new_event_loop()
    engine = create_async_engine(DATABASE_URL, pool_size=2, max_overflow=0)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        return loop.run_until_complete(coro(session_factory))
    finally:
        loop.run_until_complete(engine.dispose())
        loop.close()
```

### Test Sessions (`tests/conftest.py`)

SQLite in-memory engine is used for all tests. Fixtures `db_engine` and `db_session` provide isolated test sessions.
