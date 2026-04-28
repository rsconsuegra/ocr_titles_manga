# Architecture Overview

## System Summary

Manga OCR Title is a full-stack application for extracting manga titles from images using OCR, LLM-based extraction, and rule-based matching. It consists of a **FastAPI** backend, a **React** frontend, a **Dramatiq/Redis** async worker, and a **content-addressable image cache** — all orchestrated via Docker Compose.

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Frontend  │  │   API    │  │  Worker   │  │   Postgres 18  │  │
│  │ React 19  │──│ FastAPI  │──│ Dramatiq  │  │   + Alembic    │  │
│  │ Vite 6    │  │ Uvicorn  │  │  Redis    │  │                │  │
│  │ :5173     │  │ :8000    │  │           │  │   :5432        │  │
│  └──────────┘  └────┬─────┘  └─────┬─────┘  └───────┬────────┘  │
│                      │              │                  │           │
│                      │         ┌────┴────┐            │           │
│                      │         │  Redis  │            │           │
│                      │         │  :6379  │            │           │
│                      │         └─────────┘            │           │
│                      │              │                  │           │
│                      └──────────────┴──────────────────┘           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Processing Pipelines

The system has **two distinct processing paths**:

### 1. Queued Pipeline (Async)

```
[Upload Page]                     [Worker]
  ImageUploader                      │
    │                                │
    ▼                                │
  POST /inputs/upload                │
  + optional profile_id              │
    │                                │
    ├─ Save files to uploads/        │
    ├─ Create PipelineRun(s)         │
    │  (with config snapshot         │
    │   from profile)                │
    │                                │
    ▼                                │
  POST /pipeline/run/{id}            │
  or POST /batches/{id}/trigger      │
    │                                │
    ├─ Validate pending status       │
    ├─ Enqueue Dramatiq message ────►│
    │                                ▼
    │                          process_pipeline_run()
    │                                │
    │                          ┌─────┴──────┐
    │                          │ Load run    │
    │                          │ Set status  │
    │                          │ =processing │
    │                          └─────┬──────┘
    │                                │
    │                     ┌──────────┴──────────┐
    │                     │ Config Resolution    │
    │                     │                      │
    │                     │ if run.preprocess_   │
    │                     │   config is set:     │
    │                     │   Use snapshot       │
    │                     │ else:                │
    │                     │   Load global files  │
    │                     └──────────┬──────────┘
    │                                │
    │                          ┌─────┴──────┐
    │                          │ OCREngine  │
    │                          │ .process() │
    │                          └─────┬──────┘
    │                                │
    │                    ┌───────────┴───────────┐
    │                    │                       │
    │               Preprocessing           Run OCR Models
    │               (if enabled)           (parallel if >1)
    │                    │                       │
    │                    └───────────┬───────────┘
    │                                │
    │                    ┌───────────┴───────────┐
    │                    │                       │
    │               LLM Extraction        Rule Matching
    │               (if enable_llm)       (always)
    │                    │                       │
    │                    └───────────┬───────────┘
    │                                │
    │                          Select best title
    │                                │
    │                          Save results to DB
    │                          + update batch progress
    │                                │
    │                          Cache OCR results
    │                          via put_ocr_result()
    │                                │
    │                          Set status=completed
    ◄────────────────────────────────┘
    
    Cooperative cancellation checkpoints:
    • Before setting status=processing (check DB for cancelled)
    • Before engine.process() (check DB for cancelled)
```

### 2. Quick Run (Stateless / Synchronous)

```
[Quick Run Page]
  │
  ├─ Select image file
  ├─ Optionally configure preprocessing + OCR models
  ├─ Optionally select profile (loads defaults)
  │
  ▼
POST /run/quick
  multipart/form-data: file, preprocess_steps, ocr_models, enable_llm, profile_id
  │
  ├─ Read file bytes + decode
  ├─ If preprocess_steps: run preprocessing pipeline
  ├─ Run all enabled OCR models
  ├─ If enable_llm: run LLM extraction on best result
  │
  ▼
Return QuickRunResponse (no DB persistence)
```

---

## Component Map

```
ocr_manga_title/
├── api/                        # HTTP layer
│   ├── app.py                  # FastAPI factory + exception handlers
│   ├── dependencies.py         # get_db(), get_config()
│   ├── routes/                 # 9 route modules (33 endpoints)
│   └── schemas/                # 9 Pydantic schema modules
├── cli.py                      # Single-image CLI runner
├── config.py                   # Config file loaders (TOML, YAML)
├── db/                         # Data access layer
│   ├── models.py               # 8 ORM models
│   ├── crud.py                 # ~40 CRUD functions
│   └── session.py              # Async engine + session factory
├── engine/                     # OCR engine orchestration
│   ├── base.py                 # BaseOCRModel ABC
│   ├── registry.py             # MODEL_REGISTRY (4 models)
│   ├── ocr_engine.py           # OCREngine orchestrator
│   ├── tesseract_model.py      # Tesseract adapter (production)
│   ├── paddle_model.py         # PaddleOCR adapter (production)
│   ├── easyocr_model.py        # EasyOCR adapter (production)
│   └── glm_ocr_model.py       # Vision API adapter (production)
├── exceptions.py               # Exception hierarchy
├── postprocess/                # Post-OCR processing
│   ├── llm_extractor.py        # OpenRouter LLM extraction
│   └── rule_matcher.py         # ISBN regex + title normalization
├── preprocess/                 # Image preprocessing
│   ├── base.py                 # BasePreProcessor ABC
│   ├── registry.py             # STEP_REGISTRY (5 steps)
│   ├── pipeline.py             # PreProcessingPipeline orchestrator
│   └── steps/                  # 5 step implementations
├── schemas.py                  # Core Pydantic models
├── services/                   # Business logic layer
│   ├── config.py               # Profile snapshot builder
│   ├── cache.py                # Content-addressable image cache
│   ├── image.py                # Base64/numpy image encoding/decoding + multipart helpers
│   ├── ocr.py                  # Model execution helpers
│   ├── pipeline.py             # Result persistence
│   └── preprocess.py           # Step execution helper
├── settings.py                 # Environment variables + constants + cache settings
└── workers/                    # Background task processing
    ├── broker.py               # RedisBroker setup
    └── ocr_worker.py           # Dramatiq actor (process_pipeline_run, cooperative cancellation, OOM check)
```

---

## Exception Hierarchy

```
MangaOCRError                          → 500
├── ConfigurationError                 → 500  (bad config file/values)
├── ModelNotAvailableError             → 503  (runtime deps missing)
├── LLMExtractionError                 → 502  (API call/parse failure)
└── PermanentError                     → 400  (no retry, e.g. file not found)
```

Each exception is handled by a global handler registered in `api/app.py` that returns a structured JSON response:
```json
{ "detail": "error message", "error_code": "error_type" }
```

---

## Key Design Decisions

1. **Worker creates its own DB engine** per `_run_async()` invocation — avoids event-loop reuse bugs on Dramatiq retries. Engine is disposed after each invocation.

2. **Config snapshots, not FK references** — Profile configs are copied into `PipelineRun.preprocess_config` at creation time. Profile edits don't retroactively affect old runs.

3. **Two config paths in worker** — If `run.preprocess_config` is set, use the snapshot. If null, fall back to loading global files (backward compatibility).

4. **`MODEL_REGISTRY` is the single source of truth** — Model names, classes, and parameter descriptors are defined once in `engine/registry.py`. The `model_configs` DB table only stores runtime enable/disable and parameter overrides.

5. **`STEP_REGISTRY` same pattern** — Preprocessing step definitions live in `preprocess/registry.py`. Runtime config comes from YAML or profiles.

6. **ORM/Pydantic name collision** — `OCRResult` and `ModelConfig` exist as both ORM models and Pydantic schemas. Import aliasing (`as OCRResultDB`, `as ModelConfigSchema`) is required throughout.

7. **Naive UTC datetimes** — All timestamps use `datetime.now(UTC).replace(tzinfo=None)` for PostgreSQL compatibility.

8. **Image cache** — Content-addressable cache keyed on `(image_hash, config_hash, cache_type)`. Preprocessing and OCR results cached for 7 days. Background sweeper evicts expired entries hourly.

9. **Cooperative cancellation** — Worker checks DB for cancelled status at cooperative checkpoints. No thread interruption — graceful, DB-driven.

10. **OOM pre-flight check** — Worker reads `/proc/meminfo` before OCREngine instantiation. Raises PermanentError if < 512MB available.
