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

## Startup Sequence

The API lifespan handler runs the following steps in order:

```
Application starts (uvicorn)
  │
  ├─ 1. Verify SERVER_SECRET env var is set (required for credential encryption)
  │
  ├─ 2. Run warmup_models() in a background executor thread
  │     └─ Preloads all enabled OCR models into memory
  │        (avoids cold-start latency on first request)
  │
  └─ 3. Start cache sweeper
        └─ Hourly background task that evicts expired image cache entries
```

If `SERVER_SECRET` is missing, the application logs a warning and continues — credential encryption will not be available, and the system falls back to reading API keys from environment variables.

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
│   ├── app.py                  # FastAPI factory + exception handlers + lifespan
│   ├── dependencies.py         # get_db(), get_config()
│   ├── routes/                 # 13 route modules (48 endpoints)
│   │   ├── _helpers.py         # Shared route helpers
│   │   ├── config/             # Configuration endpoints
│   │   │   ├── catalog.py      # Catalog management
│   │   │   ├── llm.py          # LLM configuration
│   │   │   ├── ollama.py       # Ollama configuration
│   │   │   ├── profiles.py     # Profile CRUD
│   │   │   └── settings.py     # Global settings
│   │   ├── pipeline/           # Pipeline execution endpoints
│   │   │   ├── batches.py      # Batch operations
│   │   │   ├── inputs.py       # Input upload/management
│   │   │   ├── results.py      # Result retrieval
│   │   │   ├── run.py          # Single run execution
│   │   │   └── runs.py         # Run management/listing
│   │   └── ocr/                # OCR-specific endpoints
│   │       ├── models.py       # Model config CRUD
│   │       ├── ocr.py          # OCR execution
│   │       └── preprocess.py   # Preprocessing config
│   └── schemas/                # 10 Pydantic schema modules
│       ├── batch.py
│       ├── catalog.py
│       ├── models.py
│       ├── ocr.py
│       ├── ollama.py
│       ├── pipeline.py
│       ├── preprocess.py
│       ├── profiles.py
│       └── results.py
├── cli.py                      # Single-image CLI runner
├── config.py                   # Config file loaders (TOML, YAML)
├── db/                         # Data access layer
│   ├── models.py               # 10 ORM models
│   ├── crud.py                 # ~30 CRUD functions
│   ├── enums.py                # DB enum definitions
│   └── session.py              # Async engine + session factory
├── engine/                     # OCR engine orchestration
│   ├── base.py                 # BaseOCRModel ABC
│   ├── registry.py             # MODEL_REGISTRY (5 models)
│   ├── ocr_engine.py           # OCREngine orchestrator
│   ├── tesseract_model.py      # Tesseract adapter (production)
│   ├── paddle_model.py         # PaddleOCR adapter (production)
│   ├── easyocr_model.py        # EasyOCR adapter (production)
│   ├── glm_ocr_model.py       # Vision API adapter (production)
│   └── ollama_vision_model.py  # Ollama vision adapter (production)
├── exceptions.py               # Exception hierarchy
├── postprocess/                # Post-OCR processing
│   ├── llm_extractor.py        # LLM extraction (OpenRouter + Ollama)
│   └── rule_matcher.py         # ISBN regex + title normalization
├── preprocess/                 # Image preprocessing
│   ├── base.py                 # BasePreProcessor ABC
│   ├── registry.py             # STEP_REGISTRY (5 steps)
│   ├── pipeline.py             # PreProcessingPipeline orchestrator
│   └── steps/                  # 5 step implementations
├── schemas.py                  # Core Pydantic models
├── services/                   # Business logic layer
│   ├── config.py               # Profile snapshot builder
│   ├── config_live.py          # Live config resolution
│   ├── credentials.py          # Fernet encryption for API keys
│   ├── profile_import.py       # Profile import/export as JSON
│   ├── warmup.py               # Model preloading on startup
│   ├── cache.py                # Content-addressable image cache
│   ├── image.py                # Base64/numpy image encoding/decoding + multipart helpers
│   ├── ocr.py                  # Model execution helpers
│   ├── ollama.py               # Ollama provider client
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

11. **Encrypted credentials** — API keys are stored in the `api_credentials` table using Fernet symmetric encryption, with the encryption key derived from the `SERVER_SECRET` environment variable. At runtime, the system first queries the DB for a stored credential; if none exists, it falls back to the corresponding environment variable default. This allows per-instance credential management without requiring redeployment.

12. **Dual LLM providers** — Both OpenRouter and Ollama are supported as LLM backends for post-OCR extraction. The provider is selected per-profile via the `llm_provider` field (`"openrouter"` or `"ollama"`). Each provider has its own client implementation (`postprocess/llm_extractor.py` delegates to `services/ollama.py` for Ollama calls).

13. **Per-model JSON mode** — `config/llm_models.yaml` defines which LLM models support `response_format={"type": "json_object"}` via a `supports_json_mode` flag. Models with `supports_json_mode: false` are prompted in text mode, and the extractor parses the raw text response instead of expecting structured JSON. This accommodates models that don't reliably support JSON output.

14. **Model warmup** — On API startup, `warmup_models()` runs in a background executor thread to preload all enabled OCR models into memory. This eliminates cold-start latency on the first request. The warmup happens concurrently with the server accepting connections.

15. **Profile import/export** — Profiles can be exported to and imported from JSON files. Import validates the profile data against current model and preprocessing step registries, rejecting profiles that reference unknown models or steps. This enables sharing configurations across instances.
