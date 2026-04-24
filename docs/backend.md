# Backend Reference

## Module Index

| Module | Purpose |
|---|---|
| `api/app.py` | FastAPI application factory, CORS, exception handlers |
| `api/dependencies.py` | `get_db()` session dependency, `get_config()` loader |
| `api/routes/` | 9 route modules with 33 endpoints total |
| `api/schemas/` | Pydantic request/response schemas |
| `cli.py` | Single-image CLI pipeline runner |
| `config.py` | Config file loaders (TOML, YAML) with caching |
| `db/models.py` | 8 SQLAlchemy ORM models |
| `db/crud.py` | ~40 async CRUD functions |
| `db/session.py` | Async engine + session factory |
| `engine/base.py` | `BaseOCRModel` abstract base class |
| `engine/registry.py` | `MODEL_REGISTRY` — single source of truth for OCR models |
| `engine/ocr_engine.py` | `OCREngine` orchestrator |
| `engine/tesseract_model.py` | Tesseract adapter (production-ready) |
| `engine/paddle_model.py` | PaddleOCR adapter (stub) |
| `engine/easyocr_model.py` | EasyOCR adapter (stub) |
| `engine/glm_ocr_model.py` | GLM-OCR adapter (stub) |
| `exceptions.py` | Exception hierarchy |
| `postprocess/llm_extractor.py` | OpenRouter LLM title extraction |
| `postprocess/rule_matcher.py` | ISBN regex + title normalization |
| `preprocess/base.py` | `BasePreProcessor` abstract base class |
| `preprocess/registry.py` | `STEP_REGISTRY` + `STEP_ORDER` |
| `preprocess/pipeline.py` | `PreProcessingPipeline` orchestrator |
| `preprocess/steps/` | 5 preprocessing step implementations |
| `schemas.py` | Core Pydantic models (AppConfig, ModelConfig, PipelineResult, etc.) |
| `services/config.py` | `build_run_config_snapshot()` profile helper |
| `services/image.py` | Base64/numpy image encoding/decoding |
| `services/ocr.py` | Model execution helpers |
| `services/pipeline.py` | Result persistence + catalog sync |
| `services/preprocess.py` | Step execution helper |
| `settings.py` | Environment variables + constants |
| `workers/broker.py` | RedisBroker setup |
| `workers/ocr_worker.py` | Dramatiq actor `process_pipeline_run` |

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
| `paddle` | `PaddleModel` | Stub | `languages` (text) |
| `easyocr` | `EasyOCRModel` | Stub | `languages` (text) |
| `glm_ocr` | `GLMOCRModel` | Stub | `api_endpoint` (text) |

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

Sends raw OCR text to an OpenAI-compatible API (OpenRouter) and parses the structured JSON response.

**Constructor:** `LLMExtractor(config: OpenRouterConfig, prompt_path: str | None = None)`

- Creates an `openai.OpenAI` client with the configured API key, base URL, and timeout
- Loads the system prompt from `prompts/llm/extract_title_v1.md` (or uses a hardcoded fallback)
- Uses `temperature=0.1` and `response_format={"type": "json_object"}`

**`extract(raw_text, model=None) → ExtractedTitle`:**
- Sends a chat completion with system prompt + user message (raw text)
- Parses JSON from the response (tolerates markdown code fences)
- Raises `LLMExtractionError` on auth errors, API errors, or unparseable responses
- Returns `ExtractedTitle` with `title_en`, `title_ja`, `code`, `confidence`, `source_method="llm"`

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

### `services/image.py`

Base64 ↔ numpy image conversion utilities:

| Function | Input | Output |
|---|---|---|
| `decode_image(data_url)` | base64 data-URL string | numpy BGR array |
| `encode_image(image)` | numpy BGR array | base64 PNG data-URL string |
| `decode_and_save(data_url)` | base64 data-URL string | temp file path (PNG) |
| `numpy_to_temp_file(image)` | numpy array | temp file path (PNG) |

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

---

## Worker (`workers/ocr_worker.py`)

### Dramatiq Actor: `process_pipeline_run`

```python
@dramatiq.actor(max_retries=3, min_backoff=10000, max_backoff=60000, time_limit=300000)
def process_pipeline_run(run_id: str): ...
```

- **Max retries**: 3 (with exponential backoff 10s-60s)
- **Timeout**: 5 minutes
- **PermanentError**: Sets status=failed, does NOT re-raise (no retry)
- **Other exceptions**: Sets status=failed, re-raises (triggers retry)

### Worker Processing Flow

1. Creates a **new event loop + DB engine** per invocation (not shared with API)
2. Loads `PipelineRun` by UUID
3. Sets `status = "processing"`, commits
4. Verifies image file exists on disk
5. **Config resolution**:
   - If `run.preprocess_config` is set: extracts `ocr_models`, `preprocess_steps`, `enable_llm` from snapshot
   - If null: loads from global files + DB (`load_config()`, `_get_model_configs()`, `load_preprocess_config()`)
6. Creates `OCREngine` and calls `engine.process(image_path, enable_llm=enable_llm)`
7. Calls `save_pipeline_results()` to persist OCR + post-processing + catalog rows
8. Sets `status = "completed"` + `completed_at`
9. If `run.batch_run_id`: calls `update_batch_progress()` to update batch counters

### Broker (`workers/broker.py`)

Initializes a `RedisBroker` connected to `REDIS_URL` and sets it as the global Dramatiq broker. Imported as a side-effect by the worker module.

---

## CLI (`cli.py`)

Single-image pipeline runner:

```bash
python -m ocr_manga_title.cli <image_path>
```

Loads all three config files, creates an `OCREngine`, and prints the JSON result to stdout. Uses the legacy global-file path (no profiles).
