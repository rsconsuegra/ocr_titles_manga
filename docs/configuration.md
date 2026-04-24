# Configuration System

## Overview

The application has a multi-layered configuration system with both file-based and database-persisted sources. Pipeline profiles unify these into a single named entity that can be saved, reused, and snapshotted into individual runs.

---

## Configuration Sources

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Sources                      │
├──────────────────┬──────────────┬───────────────────────────┤
│ Source            │ Type         │ Used By                   │
├──────────────────┼──────────────┼───────────────────────────┤
│ config/configs.   │ TOML file    │ OCREngine (LLM creds),    │
│   toml            │ (lru_cache)  │ PreProcessingPipeline     │
│                  │              │ (debug dir)               │
├──────────────────┼──────────────┼───────────────────────────┤
│ config/ocrs.yaml  │ YAML file    │ Seed only — runtime config│
│                  │ (lru_cache)  │ lives in model_configs DB  │
├──────────────────┼──────────────┼───────────────────────────┤
│ config/           │ YAML file    │ Worker (legacy path only) │
│   preprocess.yaml │ (NOT cached) │                           │
├──────────────────┼──────────────┼───────────────────────────┤
│ settings.py       │ Env vars     │ DB URL, Redis URL,        │
│                  │ (os.getenv)  │ upload limits, CORS        │
├──────────────────┼──────────────┼───────────────────────────┤
│ model_configs     │ DB table     │ Worker (model enable/     │
│   table           │              │ params at runtime)         │
├──────────────────┼──────────────┼───────────────────────────┤
│ pipeline_profiles │ DB table     │ Upload, Batch, Quick Run  │
│   table           │              │ (named config snapshots)   │
└──────────────────┴──────────────┴───────────────────────────┘
```

---

## Config Loading Functions (`config.py`)

### `load_config(config_path) → AppConfig`

- Loads `config/configs.toml`
- Validates via Pydantic `AppConfig` (has `OpenRouterConfig` sub-model)
- **Cached** via `@lru_cache(maxsize=1)` — loaded once per process
- Raises `ConfigurationError` on missing/malformed file

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

---

## Pipeline Profiles

### What They Store

A `PipelineProfile` captures the full pipeline configuration:

```json
{
  "name": "Manga High Quality",
  "description": "Full preprocessing + Tesseract + LLM",
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

This shape exactly matches the `QuickRunRequest` schema (`preprocess_steps` + `ocr_models` + `enable_llm`).

### Snapshot Mechanism

When a run is created with a `profile_id`:

1. The profile is loaded from DB
2. `build_run_config_snapshot(profile)` in `services/config.py` extracts the JSON
3. The snapshot is stored in `PipelineRun.preprocess_config` (JSON column)
4. The worker reads this snapshot instead of global files

**Key property**: Snapshots are immutable. Editing a profile does not affect previously created runs.

### Worker Config Resolution

```python
# In workers/ocr_worker.py _process()

if run.preprocess_config:
    # Profile snapshot path
    ocr_models = run.preprocess_config.get("ocr_models", {})
    preprocess_steps = run.preprocess_config.get("preprocess_steps", {})
    enable_llm = run.preprocess_config.get("enable_llm", False)
else:
    # Legacy fallback: global files + DB
    model_configs = await _get_model_configs(session)
    preprocess_raw = load_preprocess_config(PREPROCESS_CONFIG_PATH)
    enable_llm = True
```

### Profile + Inline Overrides (Quick Run)

When Quick Run receives both a `profile_id` and inline config:

```python
# In api/routes/run.py

# 1. Load profile as base
profile_steps = profile.preprocess_steps or {}
profile_models = profile.ocr_models or {}
enable_llm = profile.enable_llm

# 2. Merge with inline overrides (inline wins)
if body.preprocess_steps:
    profile_steps = {**profile_steps, **body.preprocess_steps}
if body.ocr_models:
    profile_models = {**profile_models, **body.ocr_models}
if body.enable_llm is not None:
    enable_llm = body.enable_llm
```

---

## Default Profile

At most one profile can have `is_default = True`. When creating a run without specifying a `profile_id`, the system falls back to global files (legacy behavior). The default profile can be used by frontend UI to pre-select a profile.

Setting a profile as default automatically unsets any previous default via `_unset_default_profiles()`.

---

## Config Scope Matrix

| Flow | App Config (TOML) | OCR Models | Preprocessing | Per-Run Override | Results Persisted? |
|---|---|---|---|---|---|
| Worker (profile) | File, cached | From snapshot | From snapshot | Snapshot stored in `preprocess_config` | Yes (DB) |
| Worker (legacy) | File, cached | DB `model_configs` | File, reload | None | Yes (DB) |
| Quick Run | Loaded inside `run_llm_extraction()` | Request body or profile | Request body or profile | Full inline | No (stateless) |
| OCR Playground | Loaded inside `run_llm_extraction()` | Request body `params` | N/A | Per-model params | No |
| CLI | All 3 files loaded | `ocrs.yaml` | `preprocess.yaml` | None | No |
