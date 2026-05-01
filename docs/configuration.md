# Configuration System

## Overview

The application has a multi-layered configuration system with both file-based and database-persisted sources. Pipeline profiles unify these into a single named entity that can be saved, reused, and snapshotted into individual runs. LLM providers (OpenRouter, Ollama) are selectable per-profile, with credentials stored encrypted in the database.

---

## Configuration Sources

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Configuration Sources                                 │
├──────────────────┬──────────────┬───────────────────────────────────────────┤
│ Source            │ Type         │ Used By                                   │
├──────────────────┼──────────────┼───────────────────────────────────────────┤
│ config/configs.   │ TOML file    │ OCREngine (LLM creds), Ollama URL         │
│   toml            │ (lru_cache)  │                                           │
├──────────────────┼──────────────┼───────────────────────────────────────────┤
│ config/ocrs.yaml  │ YAML file    │ Seed only — runtime config                │
│                  │ (lru_cache)  │ lives in model_configs DB                  │
├──────────────────┼──────────────┼───────────────────────────────────────────┤
│ config/           │ YAML file    │ Worker (legacy path only)                 │
│   preprocess.yaml │ (NOT cached) │                                           │
├──────────────────┼──────────────┼───────────────────────────────────────────┤
│ config/           │ YAML file    │ LLM provider selection — model list       │
│   llm_models.yaml │ (lru_cache)  │ with JSON mode support flags              │
├──────────────────┼──────────────┼───────────────────────────────────────────┤
│ settings.py       │ Env vars     │ DB URL, Redis URL,                        │
│                  │ (os.getenv)  │ upload limits, CORS                        │
├──────────────────┼──────────────┼───────────────────────────────────────────┤
│ SERVER_SECRET     │ Env var      │ Fernet encryption key for                 │
│   env var         │              │ credential storage                        │
├──────────────────┼──────────────┼───────────────────────────────────────────┤
│ model_configs     │ DB table     │ Worker (model enable/                     │
│   table           │              │ params at runtime)                         │
├──────────────────┼──────────────┼───────────────────────────────────────────┤
│ pipeline_profiles │ DB table     │ Upload, Batch, Quick Run                  │
│   table           │              │ (named config snapshots)                   │
├──────────────────┼──────────────┼───────────────────────────────────────────┤
│ api_credentials   │ DB table     │ Encrypted API key storage                 │
│   table           │              │ (OpenRouter, Ollama)                       │
└──────────────────┴──────────────┴───────────────────────────────────────────┘
```

---

## Config Loading Functions (`config.py`)

### `load_config(config_path) → AppConfig`

- Loads `config/configs.toml`
- Validates via Pydantic `AppConfig` (has `OpenRouterConfig` sub-model)
- **Cached** via `@lru_cache(maxsize=1)` — loaded once per process
- Raises `ConfigurationError` on missing/malformed file
- Note: `images_path` was removed from configs.toml. `IMAGES_PATH` now comes from env var in `settings.py`

### `load_ocr_config(config_path) → dict[str, ModelConfig]`

- Loads `config/ocrs.yaml`
- Expects top-level `models` key
- Routes unknown fields into `parameters` dict (with typo detection via Levenshtein)
- **Cached** via `@lru_cache(maxsize=1)`
- Only used for seeding; runtime config comes from DB

### `load_preprocess_config(config_path) → dict`

- Loads `config/preprocess.yaml`
- Returns raw dict (not Pydantic model)
- **NOT cached** — reloaded each call
- Returns `{"preprocessing": {"enabled": False}}` if file missing (graceful degradation)
- Used by worker's legacy path when no profile snapshot exists

### `load_openrouter_models(config_path) → list[dict]`

- Loads `config/llm_models.yaml`
- Returns list of model descriptors, each with:
  - `id` — model identifier (e.g. `google/gemini-2.5-flash`)
  - `label` — human-readable display name
  - `supports_json_mode` — boolean, defaults to `True` if omitted
- **Cached** via `@lru_cache(maxsize=1)`
- Used by LLM provider selection to determine per-model JSON vs text mode

---

## Ollama Configuration

### Schema (`schemas.py`)

`OllamaConfig` is a Pydantic model with the following fields:

| Field | Type | Description |
|---|---|---|
| `base_url` | `str` | Ollama API base URL (e.g. `http://localhost:11434`) |
| `default_model` | `str` | Default text generation model |
| `default_vision_model` | `str` | Default vision-capable model |
| `timeout` | `int` | Request timeout in seconds |

### Live Config (`services/config_live.py`)

Ollama URL can be changed at runtime without restarting the server:

- Reads/writes `configs.toml` `[ollama]` section
- `lru_cache` on the config loader is **invalidated on writes** so changes take effect immediately
- Frontend settings page calls the config API endpoint to update

### Environment Variables

| Variable | Description |
|---|---|
| `OLLAMA_BASE_URL` | Overrides the Ollama API base URL |
| `OLLAMA_API_KEY` | Optional API key for Ollama proxy |
| `OLLAMA_TIMEOUT` | Request timeout in seconds |
| `OLLAMA_DEFAULT_MODEL` | Default text generation model name |

---

## LLM Provider Selection

### Pipeline Profile Fields

`PipelineProfile` includes two fields that control LLM behavior:

| Field | Type | Values |
|---|---|---|
| `llm_provider` | `str` | `"openrouter"` or `"ollama"` |
| `llm_config` | `JSON` dict | Provider-specific configuration |

### LLMPromptConfig Schema

`LLMPromptConfig` in `schemas.py`:

| Field | Type | Description |
|---|---|---|
| `system_prompt` | `str` | System message for LLM |
| `user_prompt_template` | `str` | Template with `{ocr_text}` placeholder |
| `temperature` | `float` | Sampling temperature |
| `max_ocr_chars` | `int` | Max OCR text length sent to LLM |
| `llm_model` | `str` | Model identifier to use |
| `reasoning_enabled` | `bool` | Enable reasoning/thinking mode |

- `from_dict(data: dict) → LLMPromptConfig` — class method, constructs from the JSON dict stored in `llm_config`
- `render_user_prompt(ocr_text: str) → str` — substitutes `{ocr_text}` into `user_prompt_template`

### Per-Model JSON Mode

`config/llm_models.yaml` defines `supports_json_mode` per model. During LLM calls:

- Models with `supports_json_mode: true` (or omitted, since default is `True`) use `response_format={"type": "json_object"}`
- Models with `supports_json_mode: false` fall back to plain text mode and rely on prompt instructions for structured output

---

## Credential Storage

### `services/credentials.py`

Provides encrypted storage for API keys used by LLM providers.

### Encryption

- Uses Fernet symmetric encryption (from the `cryptography` library)
- Encryption key comes from the `SERVER_SECRET` environment variable
- All keys are encrypted at rest in the `api_credentials` database table

### Lookup Order

```
1. Check api_credentials DB table (encrypted)
2. Fall back to environment variable for the service
```

### Supported Services

| Service | DB Key | Env Var Fallback |
|---|---|---|
| `openrouter` | `openrouter_api_key` | `OPENROUTER_API_KEY` |
| `ollama` | `ollama_api_key` | `OLLAMA_API_KEY` |

---

## Cache Settings (`settings.py`)

| Setting | Default | Description |
|---|---|---|
| `CACHE_DIR` | `/app/cache` | Directory for cached preprocessing/OCR files |
| `CACHE_TTL_DAYS` | `7` | Days before cache entries expire |
| `CACHE_SWEEPER_INTERVAL_SECONDS` | `3600` | Background sweeper run interval (seconds) |
| `IMAGES_PATH` | `/app/uploads` | Debug image output (env var override) |

The cache sweeper runs as a background task in the FastAPI lifespan (`api/app.py`).

---

## Pipeline Profiles

### What They Store

A `PipelineProfile` captures the full pipeline configuration:

```json
{
  "name": "Manga High Quality",
  "description": "Full preprocessing + Tesseract + LLM",
  "llm_provider": "openrouter",
  "llm_config": {
    "system_prompt": "...",
    "user_prompt_template": "...",
    "temperature": 0.1,
    "max_ocr_chars": 5000,
    "llm_model": "google/gemini-2.5-flash",
    "reasoning_enabled": false
  },
  "preprocess_steps": {
    "grayscale": {"enabled": true},
    "upscale": {"enabled": true, "method": "cubic", "scale_factor": 2},
    "denoise": {"enabled": true, "method": "gaussian", "strength": "light"},
    "binarize": {"enabled": true, "method": "otsu"}
  },
  "ocr_models": {
    "tesseract": {"enabled": true, "languages": ["eng", "jpn"], "psm": 6, "oem": 3}
  },
  "enable_llm": true,
  "is_default": false
}
```

This shape exactly matches the `QuickRunRequest` schema (`preprocess_steps` + `ocr_models` + `enable_llm` + `llm_provider` + `llm_config`).

### Snapshot Mechanism

When a run is created with a `profile_id`:

1. The profile is loaded from DB
2. `build_run_config_snapshot(profile)` in `services/config.py` extracts the JSON
3. The snapshot is stored in `PipelineRun.preprocess_config` (JSON column)
4. The worker reads this snapshot instead of global files

**Key property**: Snapshots are immutable. Editing a profile does not affect previously created runs.

### Worker Config Resolution

```python
if run.preprocess_config:
    ocr_models = run.preprocess_config.get("ocr_models", {})
    preprocess_steps = run.preprocess_config.get("preprocess_steps", {})
    enable_llm = run.preprocess_config.get("enable_llm", False)
    llm_provider = run.preprocess_config.get("llm_provider", "openrouter")
    llm_config = run.preprocess_config.get("llm_config", {})
else:
    model_configs = await _get_model_configs(session)
    preprocess_raw = load_preprocess_config(PREPROCESS_CONFIG_PATH)
    enable_llm = True
    llm_provider = "openrouter"
    llm_config = {}
```

### Profile + Inline Overrides (Quick Run)

When Quick Run receives both a `profile_id` and inline config:

```python
profile_steps = profile.preprocess_steps or {}
profile_models = profile.ocr_models or {}
enable_llm = profile.enable_llm
llm_provider = profile.llm_provider
llm_config_data = profile.llm_config or {}

if body.preprocess_steps:
    profile_steps = {**profile_steps, **body.preprocess_steps}
if body.ocr_models:
    profile_models = {**profile_models, **body.ocr_models}
if body.enable_llm is not None:
    enable_llm = body.enable_llm
if body.llm_provider:
    llm_provider = body.llm_provider
if body.llm_config:
    llm_config_data = {**llm_config_data, **body.llm_config}
```

---

## Default Profile

At most one profile can have `is_default = True`. When creating a run without specifying a `profile_id`, the system falls back to global files (legacy behavior). The default profile can be used by frontend UI to pre-select a profile.

Setting a profile as default automatically unsets any previous default via `_unset_default_profiles()`.

---

## Config Scope Matrix

| Flow | App Config (TOML) | OCR Models | Preprocessing | LLM Provider | LLM Config | Per-Run Override | Results Persisted? |
|---|---|---|---|---|---|---|---|
| Worker (profile) | File, cached | From snapshot | From snapshot | From snapshot | From snapshot | Snapshot stored in `preprocess_config` | Yes (DB) |
| Worker (legacy) | File, cached | DB `model_configs` | File, reload | `openrouter` | `{}` | None | Yes (DB) |
| Quick Run | Loaded inside `run_llm_extraction()` | Request body or profile | Request body or profile | Request body or profile | Request body or profile | Full inline | No (stateless) |
| OCR Playground | Loaded inside `run_llm_extraction()` | Request body `params` | N/A | `openrouter` | From request | Per-model params | No |
| CLI | All 3 files loaded | `ocrs.yaml` | `preprocess.yaml` | `openrouter` | `{}` | None | No |
