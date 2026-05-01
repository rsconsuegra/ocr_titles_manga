# Backend Reference

## Module Index

| Module | Purpose |
|---|---|
| `api/app.py` | FastAPI application factory, CORS, exception handlers |
| `api/dependencies.py` | `get_db()` session dependency, `get_config()` loader |
| `api/routes/config/` | Settings, Ollama, LLM, profiles, catalog routes (5 files, 25 endpoints) |
| `api/routes/pipeline/` | Runs, batches, inputs, results, run routes (5 files, 14 endpoints) |
| `api/routes/ocr/` | OCR, preprocessing, models routes (3 files, 9 endpoints) |
| `api/routes/_helpers.py` | Shared response helpers |
| `api/schemas/` | 10 Pydantic request/response schema modules |
| `api/schemas/ollama.py` | Ollama-related schemas |
| `cli.py` | Single-image CLI pipeline runner |
| `config.py` | Config file loaders (TOML, YAML) with caching |
| `db/models.py` | 10 SQLAlchemy ORM models |
| `db/crud.py` | ~30 async CRUD functions |
| `db/session.py` | Async engine + session factory |
| `engine/base.py` | `BaseOCRModel` abstract base class |
| `engine/registry.py` | `MODEL_REGISTRY` — single source of truth for OCR models |
| `engine/ocr_engine.py` | `OCREngine` orchestrator |
| `engine/tesseract_model.py` | Tesseract adapter (production-ready) |
| `engine/paddle_model.py` | PaddleOCR adapter (production-ready, multilingual, GPU) |
| `engine/easyocr_model.py` | EasyOCR adapter (production-ready, multilingual, GPU) |
| `engine/glm_ocr_model.py` | Vision API adapter (production-ready, OpenAI-compatible) |
| `engine/ollama_vision_model.py` | Ollama Vision OCR adapter (production-ready, multimodal) |
| `exceptions.py` | Exception hierarchy |
| `postprocess/llm_extractor.py` | OpenRouter / Ollama LLM title extraction |
| `postprocess/rule_matcher.py` | ISBN regex + title normalization |
| `preprocess/base.py` | `BasePreProcessor` abstract base class |
| `preprocess/registry.py` | `STEP_REGISTRY` + `STEP_ORDER` |
| `preprocess/pipeline.py` | `PreProcessingPipeline` orchestrator |
| `preprocess/steps/` | 5 preprocessing step implementations |
| `schemas.py` | Core Pydantic models (AppConfig, ModelConfig, PipelineResult, etc.) |
| `services/config.py` | `build_run_config_snapshot()` profile helper |
| `services/cache.py` | Content-addressable image cache (hash, CRUD, async wrappers) |
| `services/image.py` | Base64/numpy image encoding/decoding + multipart upload helpers |
| `services/ocr.py` | Model execution helpers |
| `services/pipeline.py` | Result persistence + catalog sync |
| `services/preprocess.py` | Step execution helper |
| `services/ollama.py` | Ollama HTTP client (model discovery, completions) |
| `services/credentials.py` | Fernet-encrypted credential storage |
| `services/config_live.py` | Live TOML config read/write for Ollama settings |
| `services/profile_import.py` | Profile import/export validation |
| `services/warmup.py` | OCR model warmup on startup |
| `settings.py` | Environment variables + constants + cache settings |
| `workers/broker.py` | RedisBroker setup |
| `workers/ocr_worker.py` | Dramatiq actor with cooperative cancellation + OOM check + model warmup |

---

## OCR Engine

### `BaseOCRModel` (`engine/base.py`)

Abstract interface that all OCR adapters must implement:

```python
class BaseOCRModel(ABC):
    def __init__(self, config: ModelConfig) -> None: ...
    @property
    def name(self) -> str: ...
    @property
    def is_available(self) -> bool: ...
    def run(self, image_path: str) -> OCRResult: ...
```

### `MODEL_REGISTRY` (`engine/registry.py`)

Frozen dict mapping model name → `ModelDescriptor`. Each descriptor contains:
- `name`: Machine identifier (e.g. `"tesseract"`)
- `label`: Human-readable label (e.g. `"Tesseract"`)
- `description`: What the model does
- `model_cls`: The `BaseOCRModel` subclass
- `params`: List of `ParamDescriptor` for UI rendering

**Registered models:**

| Name | Class | Status | Parameters |
|---|---|---|---|
| `tesseract` | `TesseractModel` | **Production** | `languages` (multiselect), `psm` (0-13), `oem` (0-3) |
| `paddle` | `PaddleModel` | **Production** | `languages` (multiselect: en, ja, ch, ko, spa, fra, deu, por, ita), `use_gpu` (boolean) |
| `easyocr` | `EasyOCRModel` | **Production** | `languages` (multiselect: en, ja, ch_sim, ch_tra, ko, es, fr, de, pt, it), `gpu` (boolean) |
| `glm_ocr` | `GLMOCRModel` | **Production** | `api_endpoint` (text), `model` (text), `api_key` (text), `prompt` (text) |
| `ollama_vision` | `OllamaVisionModel` | **Production** | `model` (text), `base_url` (text) |

**Adding a new model:**
1. Create a new file in `engine/` implementing `BaseOCRModel`
2. Add a `ModelDescriptor` entry in `_build_registry()` in `engine/registry.py`
3. Add a seed entry in migration or via the models API

### `OCREngine` (`engine/ocr_engine.py`)

The main orchestrator. Accepts three configs at construction:

```python
engine = OCREngine(
    config=app_config,           # AppConfig (TOML) — has OpenRouter creds
    ocr_config=model_configs,    # dict[str, ModelConfig] — enabled models
    preprocess_config=pp_config, # dict | None — preprocessing pipeline config
)
```

**`process(image_path, enable_llm=True)` pipeline:**
1. Validate image exists and format is supported
2. If preprocessing enabled: run `PreProcessingPipeline.process()`
3. Run all initialized OCR models (parallel via `ThreadPoolExecutor` if >1)
4. If `enable_llm=True`: run LLM extraction on each result, then rule matching augmentation
5. If no LLM results or all zero-confidence: fall back to pure rule matching
6. Select best extracted title by confidence
7. Return `PipelineResult`

**Model initialization** happens at construction time:
- Iterates `ocr_config`, checks each against `MODEL_REGISTRY`
- Skips disabled, unknown, or unavailable models
- Logs extensively

---

## Preprocessing Pipeline

### `BasePreProcessor` (`preprocess/base.py`)

```python
class BasePreProcessor(ABC):
    @property
    def name(self) -> str: ...
    @property
    def is_available(self) -> bool: ...
    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]: ...
```

### `STEP_REGISTRY` and `STEP_ORDER` (`preprocess/registry.py`)

Steps are always executed in this fixed order:

| Order | Name | Class | Purpose | Parameters |
|---|---|---|---|---|
| 1 | `roi` | `ROIStep` | Region of interest detection via contour | `method`, `min_area`, `padding`, `merge_overlap` |
| 2 | `grayscale` | `GrayscaleStep` | BGR → single-channel | (none) |
| 3 | `upscale` | `UpscaleStep` | Resolution increase | `method` (cubic/fsrcnn/edsr), `scale_factor` |
| 4 | `denoise` | `DenoiseStep` | Noise reduction | `method` (gaussian/median/nlmeans), `strength` |
| 5 | `binarize` | `BinarizeStep` | Binary thresholding | `method` (otsu/adaptive_*), `invert`, `block_size`, `c` |

### `PreProcessingPipeline` (`preprocess/pipeline.py`)

Configured from the `preprocess.yaml` shape (or a profile snapshot). Each step can be individually enabled/disabled. Supports debug mode that saves intermediate images to `{images_path}/.preprocess/`.

---

## Post-Processing

### `LLMExtractor` (`postprocess/llm_extractor.py`)

Sends raw OCR text to an OpenAI-compatible API (OpenRouter) or native Ollama `/api/chat` endpoint and parses the structured JSON response.

**Constructor:** `LLMExtractor(openrouter_config=None, ollama_config=None, provider="openrouter", prompt_path=None, prompt_config=None)`

Supports two backends:
- **openrouter** — OpenAI-compatible API via the `openai` client
- **ollama** — Native Ollama `/api/chat` endpoint via `httpx`

- Creates an `openai.OpenAI` client with the configured API key, base URL, and timeout (when using openrouter)
- Loads the system prompt from `prompts/llm/extract_title_v1.md` (or uses a hardcoded fallback)
- Uses `temperature=0.1` and `response_format={"type": "json_object"}`

**`extract(raw_text, model=None, *, supports_json_mode=True) → ExtractedTitle`:**
- Sends a chat completion with system prompt + user message (raw text)
- Supports per-model JSON mode via `supports_json_mode` flag — when `True`, uses `response_format={"type": "json_object"}`; when `False`, skips it and relies on prompt instructions
- Parses JSON from the response (tolerates markdown code fences)
- Raises `LLMExtractionError` on auth errors, API errors, or unparseable responses
- The `_build_result()` method separates `_CORE_FIELDS` (`title_en`, `title_ja`, `code`, `confidence`) from extra fields
- Returns `ExtractedTitle` with core fields plus `extra_metadata` dict containing `author`, `social_page`, and other non-core fields
- Logs response length

**Field alias resolution:** `_normalize_keys()` maps common LLM aliases (e.g. `manga_name` → `title_en`, `sauce` → `code`, `artist` → `author`) to canonical field names.

### `RuleMatcher` (`postprocess/rule_matcher.py`)

Regex-based ISBN extraction and title normalization. No external dependencies.

**`match(text) → ExtractedTitle`:**
- Searches for ISBN-13 and ISBN-10 patterns (ISBN-13 checked first)
- Validates check digits
- Returns `confidence=0.9` if found, `0.0` otherwise

**`augment(existing, text) → ExtractedTitle`:**
- Supplements an LLM-extracted title with rule-based data
- Fills in missing `code` from ISBN regex
- Normalizes titles (NFC, whitespace collapse, trailing punctuation removal)
- Sets `source_method="llm+rules"` when both contributed

**Static utilities:**
- `normalize_title(title)` — NFC normalize, collapse whitespace, strip trailing punctuation
- `normalize_isbn(isbn)` — Strip prefixes, hyphens, spaces
- `_validate_isbn13(isbn)` / `_validate_isbn10(isbn)` — Check digit validation

---

## Services Layer

### `services/cache.py`

Content-addressable cache for preprocessed images and OCR results.

| Function | Purpose |
|---|---|
| `hash_bytes(data)` | SHA-256 hex digest of raw bytes |
| `hash_config(config)` | SHA-256 hex digest of JSON-serialized config |
| `get_preprocessed(session, image_hash, config_hash)` | Lookup cached preprocessed image |
| `put_preprocessed(session, image_hash, config_hash, path)` | Store preprocessed cache entry |
| `get_ocr_result(session, image_hash, config_hash)` | Lookup cached OCR result |
| `put_ocr_result(session, image_hash, config_hash, data)` | Store OCR cache entry |
| `evict_expired(session)` | Delete all expired cache entries |
| `run_preprocessing_cached(session, image_bytes, steps_config, ...)` | Cached preprocessing wrapper |
| `run_ocr_cached(session, image_bytes, model_name, params, ...)` | Cached single-model OCR wrapper |
| `run_all_models_cached(session, image_bytes, ocr_config, ...)` | Cached multi-model OCR wrapper |

### `services/image.py`

Base64 ↔ numpy image conversion utilities:

| Function | Input | Output |
|---|---|---|
| `decode_image(data_url)` | base64 data-URL string | numpy BGR array |
| `encode_image(image)` | numpy BGR array | base64 PNG data-URL string |
| `decode_and_save(data_url)` | base64 data-URL string | temp file path (PNG) |
| `numpy_to_temp_file(image)` | numpy array | temp file path (PNG) |
| `save_bytes(raw)` | raw image bytes | temp file path (PNG) |
| `decode_bytes(raw)` | raw image bytes | numpy BGR array |
| `decode_upload(file)` | UploadFile | numpy BGR array |

### `services/ocr.py`

OCR model execution helpers:

| Function | Purpose |
|---|---|
| `build_model_config(name, overrides)` | Merge registry defaults with user overrides → `(ModelConfig, model_cls)` |
| `run_single_model(name, image_path, overrides)` | Instantiate and run one model, return `OCRResultData` |
| `run_all_enabled_models(image_path, ocr_config)` | Iterate `MODEL_REGISTRY`, run all enabled models |
| `run_llm_extraction(raw_text)` | Run LLM extraction on text, return `LLMResultData` |
| `check_model_availability(name)` | Check if model's runtime deps are installed |

### `services/pipeline.py`

Result persistence:

| Function | Purpose |
|---|---|
| `save_pipeline_results(session, run_id, result)` | Persist OCR results, post-processing results, and catalog entry |
| `override_and_sync(session, result_id, updates)` | Override post-processing fields + sync to catalog |

### `services/preprocess.py`

| Function | Purpose |
|---|---|
| `get_step_instance(name)` | Instantiate a preprocessing step by name |
| `run_preprocessing_pipeline(data_url, steps_config)` | Run preprocessing on a data URL, return temp file path |

### `services/config.py`

| Function | Purpose |
|---|---|
| `build_run_config_snapshot(profile)` | Extract JSON snapshot from a `PipelineProfile` for storage in `PipelineRun.preprocess_config` |

### `services/ollama.py`

Ollama HTTP client — model discovery and chat completions via native API:

| Function | Purpose |
|---|---|
| `list_models()` | GET `/api/tags` — list available Ollama models with metadata (cached 5 min) |
| `list_vision_models()` | List models with `vision` capability (queries `/api/show` per model, cached) |
| `is_ollama_configured()` | Return `True` if `OLLAMA_BASE_URL` is set |
| `chat_completion(model, messages, ...)` | POST `/api/chat` — async non-streaming chat completion |
| `chat_completion_sync(model, messages, ...)` | Synchronous version for use in OCR adapters |
| `invalidate_cache()` | Clear the in-process model list cache |

### `services/credentials.py`

Fernet-encrypted credential storage for external API services:

| Function | Purpose |
|---|---|
| `encrypt_value(plain)` | Encrypt a plaintext string using Fernet symmetric encryption |
| `decrypt_value(token)` | Decrypt a Fernet-encrypted token back to plaintext |
| `get_active_key(session, service_name, env_default)` | Return decrypted active API key for a service (DB first, then env fallback) |
| `store_key(session, service_name, api_key)` | Encrypt and upsert an API key for a service |
| `deactivate_key(session, service_name)` | Remove stored key (revert to env default) |
| `get_credential_info(session, service_name, env_default)` | Return credential status for the UI (masked key, source, active) |
| `validate_openrouter_key(api_key)` | Test an OpenRouter key by making a lightweight `/models` request |

### `services/config_live.py`

Live TOML config read/write for Ollama settings (thread-safe, invalidates config cache on writes):

| Function | Purpose |
|---|---|
| `read_toml()` | Read and parse the current `configs.toml` |
| `get_ollama_base_url()` | Return the current `ollama.base_url` from TOML |
| `get_ollama_default_model()` | Return the default Ollama LLM model from TOML |
| `get_ollama_default_vision_model()` | Return the default Ollama vision model from TOML |
| `get_ollama_config()` | Return the full `[ollama]` section from TOML |
| `write_ollama_base_url(new_url)` | Update `ollama.base_url` in TOML + invalidate caches |
| `write_ollama_models(default_model, default_vision_model)` | Update default model settings in TOML + invalidate caches |
| `ping_ollama(base_url)` | Ping an Ollama instance to verify connectivity (async) |

### `services/profile_import.py`

Profile import/export validation:

| Function / Class | Purpose |
|---|---|
| `validate_profile_data(profile_data)` | Validate raw profile data, return `ProfileValidationResult` with errors/warnings |
| `resolve_name_conflict(session, name)` | Append numeric suffix until name is unique (async) |
| `ProfileValidationResult` | Dataclass with `warnings`, `errors` lists and `is_valid` property |
| `ValidationMessage` | Single validation message tied to a field |

### `services/warmup.py`

| Function | Purpose |
|---|---|
| `warmup_models()` | Pre-load all local OCR models (paddle, easyocr, tesseract), return names that succeeded |

---

## Settings (`settings.py`)

Module-level constants loaded from environment variables at import time:

| Constant | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://manga_ocr:manga_ocr_dev@localhost:5432/manga_ocr` | Primary database |
| `DB_POOL_SIZE` | 5 | API connection pool size |
| `DB_MAX_OVERFLOW` | 10 | API pool overflow |
| `DB_POOL_TIMEOUT` | 30 | Pool timeout (seconds) |
| `DB_WORKER_POOL_SIZE` | 2 | Worker connection pool |
| `DB_WORKER_MAX_OVERFLOW` | 0 | Worker pool overflow |
| `REDIS_URL` | `redis://localhost:6379` | Dramatiq broker |
| `CONFIG_PATH` | `config/configs.toml` | Main config file |
| `OCR_CONFIG_PATH` | `config/ocrs.yaml` | OCR model config |
| `PREPROCESS_CONFIG_PATH` | `config/preprocess.yaml` | Preprocessing config |
| `LLM_MODELS_PATH` | `config/llm_models.yaml` | LLM model definitions |
| `UPLOAD_DIR` | `uploads` | File upload directory |
| `ALLOWED_EXTENSIONS` | `.png .jpg .jpeg .webp .tiff .tif .bmp` | Accepted image formats |
| `MAX_FILE_SIZE` | 20 MB | Per-file upload limit |
| `MAX_FILES` | 10 | Per-request file count limit |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |
| `OPENROUTER_DEFAULT_MODEL` | `google/gemini-2.5-flash` | LLM model |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | LLM API base URL |
| `OPENROUTER_REQUEST_TIMEOUT` | 30.0 | LLM request timeout |
| `OPENROUTER_MAX_RETRIES` | 3 | LLM retry count |
| `OPENROUTER_API_KEY_PREFIX` | `sk-` | API key validation prefix |
| `OPENROUTER_API_KEY` | `""` | OpenRouter API key (from env) |
| `OLLAMA_BASE_URL` | `""` | Ollama API base URL (from env) |
| `OLLAMA_API_KEY` | `ollama` | Ollama API key (from env) |
| `OLLAMA_TIMEOUT` | 120.0 | Ollama request timeout |
| `OLLAMA_DEFAULT_MODEL` | `llama3` | Default Ollama model |
| `WORKER_THREADS` | 1 | Worker thread count |
| `WORKER_PROCESSES` | 1 | Worker process count |
| `SERVER_SECRET` | `""` | Fernet encryption key for credential storage (from env) |
| `IMAGES_PATH` | `/app/uploads` | Debug image output directory |
| `CACHE_DIR` | `/app/cache` | Image cache storage directory |
| `CACHE_TTL_DAYS` | `7` | Cache entry TTL (days) |
| `CACHE_SWEEPER_INTERVAL_SECONDS` | `3600` | Background sweeper interval |

---

## Worker (`workers/ocr_worker.py`)

### Model Warmup

On module import (when logging handlers are configured), the worker calls `warmup_models()` from `services/warmup.py`. This pre-loads all local OCR models (paddle, easyocr, tesseract) so that first requests do not incur cold-start latency.

### Dramatiq Actor: `process_pipeline_run`

```python
@dramatiq.actor(max_retries=3, min_backoff=10000, max_backoff=60000, time_limit=900000)
def process_pipeline_run(run_id: str): ...
```

- **Max retries**: 3 (with exponential backoff 10s-60s)
- **Timeout**: 15 minutes
- **PermanentError**: Sets status=failed, does NOT re-raise (no retry)
- **RunCancelled**: Sets status=failed, does NOT re-raise (no retry)
- **Other exceptions**: Sets status=failed, re-raises (triggers retry)

### Worker Processing Flow

1. Creates a **new event loop + DB engine** per invocation (not shared with API)
2. Loads `PipelineRun` by UUID
3. **Cooperative checkpoint**: checks DB for cancelled status before proceeding
4. Sets `status = "processing"`, commits
5. **OOM pre-flight check**: `_check_available_memory()` reads `/proc/meminfo`, raises PermanentError if < 512MB available
6. Verifies image file exists on disk
7. **Config resolution**:
   - If `run.preprocess_config` is set: extracts `ocr_models`, `preprocess_steps`, `enable_llm`, `llm_provider`, `llm_config` from snapshot
   - If null: loads from global files + DB (`load_config()`, `_get_model_configs()`, `load_preprocess_config()`)
8. **Cooperative checkpoint**: checks DB for cancelled status before engine instantiation
9. Creates `OCREngine` and calls `engine.process(image_path, enable_llm=enable_llm)`
10. Calls `put_ocr_result()` to cache OCR results
11. Calls `save_pipeline_results()` to persist OCR + post-processing + catalog rows
12. Sets `status = "completed"` + `completed_at`
13. If `run.batch_run_id`: calls `update_batch_progress()` to update batch counters

### Broker (`workers/broker.py`)

Initializes a `RedisBroker` connected to `REDIS_URL` and sets it as the global Dramatiq broker. Imported as a side-effect by the worker module.

---

## CLI (`cli.py`)

Single-image pipeline runner:

```bash
python -m ocr_manga_title.cli <image_path>
```

Loads all three config files, creates an `OCREngine`, and prints the JSON result to stdout. Uses the legacy global-file path (no profiles).
