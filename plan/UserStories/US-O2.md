# US-O2: Load Configuration from Files

**Phase**: 0 (OCR Engine) — Sub-phase 0A  
**Priority**: Critical (blocking — all other stories depend on this)  
**Status**: Planned

---

## Story

> As an operator, I want the engine to read its settings from `configs.toml` and `ocrs.yaml` so that I can change OCR models, LLM provider, and parameters without editing source code.

---

## Scope

### In Scope
- Parse `configs.toml` into typed `AppConfig` Pydantic model
- Parse `ocrs.yaml` into typed `ModelConfig` Pydantic models (one per model)
- Custom exception hierarchy: `MangaOCRError`, `ConfigurationError`
- Validation of required fields with clear error messages
- Default values for optional fields
- Graceful handling of unknown/extra fields

### Out of Scope
- Agenta.ai configuration (Phase 2)
- Database configuration (Phase 1)
- Redis configuration (Phase 1)
- Environment variable overrides (Phase 4)
- Config file creation/writing
- Config hot-reloading (watching file changes)

---

## Preconditions

1. Project structure exists: `manga_ocr/` package directory created
2. `pyproject.toml` has `pydantic>=2.0`, `pyyaml`, `tomli` in dependencies
3. `configs.toml` and `ocrs.yaml` exist at project root (even if partially filled)
4. Python 3.12+ environment activated via `uv`

---

## Implementation Details

### File: `manga_ocr/exceptions.py`

Define exception hierarchy:
```
MangaOCRError(Exception)             # base for all project errors
  ConfigurationError(MangaOCRError)  # config file issues
  ModelNotAvailableError(MangaOCRError)  # placeholder for Phase 0B
  LLMExtractionError(MangaOCRError)     # placeholder for Phase 0C
```

Each exception should include a helpful message string. `ConfigurationError` constructor accepts `field_name` and `file_path` kwargs for structured error context.

### File: `manga_ocr/schemas.py`

Define Pydantic v2 models:

```
OpenRouterConfig:
  api_key: str                           # required, must start with "sk-"
  default_model: str = "google/gemini-2.5-flash"
  base_url: str = "https://openrouter.ai/api/v1"

  @field_validator("api_key")
  def validate_api_key(cls, v): # must start with "sk-", raise ConfigurationError if not

AppConfig:
  images_path: Path                      # required
  openrouter: OpenRouterConfig           # required

  @field_validator("images_path")
  def validate_images_path(cls, v): # warn (logging.warning) if path doesn't exist, but don't raise

ModelConfig:
  name: str                              # required, model identifier
  enabled: bool = True                   # default True if missing in yaml
  language: str | list[str] = "en"       # default "en"
  parameters: dict[str, Any] = {}        # catch-all for extra model params

  @model_validator(mode="before")
  def extract_name_from_dict_key(cls, data): # the yaml key IS the name, inject it
```

### File: `manga_ocr/config.py`

Two public functions:

```
def load_config(config_path: str | Path = "configs.toml") -> AppConfig:
    """
    1. Read file using tomli (Python < 3.11) or tomllib (Python >= 3.11)
    2. Parse into AppConfig via Pydantic
    3. Raise ConfigurationError with field name and file path on validation failure
    4. Return typed AppConfig
    """

def load_ocr_config(config_path: str | Path = "ocrs.yaml") -> dict[str, ModelConfig]:
    """
    1. Read file using PyYAML (yaml.safe_load)
    2. Parse "models" top-level key
    3. Each sub-key becomes a ModelConfig.name
    4. Unknown model names logged as warnings, not errors
    5. Missing "models" key raises ConfigurationError
    6. Return dict mapping model name -> ModelConfig
    """
```

Handle edge cases:
- File not found: raise `ConfigurationError(f"Configuration file not found: {path}")`
- File is empty: raise `ConfigurationError(f"Configuration file is empty: {path}")`
- Invalid TOML/YAML syntax: catch parse errors, wrap in `ConfigurationError`
- `images_path` doesn't exist: log warning but don't raise (may not have images yet)
- `openrouter.api_key` missing or empty: raise `ConfigurationError` with clear message
- `openrouter.api_key` doesn't start with `sk-`: raise `ConfigurationError`
- Unknown fields in yaml model blocks: silently included in `parameters` dict
- Unknown model names (not in known set): log warning

### File: `configs.toml` (update existing)

```toml
images_path = "/Users/rconsuegra/Pictures"

[openrouter]
api_key = "sk-or-..."
default_model = "google/gemini-2.5-flash"
base_url = "https://openrouter.ai/api/v1"
```

### File: `ocrs.yaml` (update existing)

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

---

## Postconditions

1. `load_config()` returns a valid `AppConfig` when `configs.toml` is valid
2. `load_ocr_config()` returns a dict of 5 `ModelConfig` objects when `ocrs.yaml` is valid
3. Missing required fields raise `ConfigurationError` with the field name and file path in the message
4. `manga_ocr.config` and `manga_ocr.schemas` are importable without errors
5. All downstream components can import types from `manga_ocr.schemas`

---

## Validation Checklist

- [ ] `load_config("configs.toml")` returns `AppConfig` with correct values
- [ ] `load_config("nonexistent.toml")` raises `ConfigurationError`
- [ ] `load_config()` with empty file raises `ConfigurationError`
- [ ] `load_config()` with missing `openrouter` section raises `ConfigurationError`
- [ ] `load_config()` with missing `openrouter.api_key` raises `ConfigurationError`
- [ ] `load_config()` with invalid api key (no `sk-` prefix) raises `ConfigurationError`
- [ ] `load_config()` with missing `images_path` raises `ConfigurationError`
- [ ] `load_config()` with nonexistent `images_path` logs warning but succeeds
- [ ] `load_ocr_config("ocrs.yaml")` returns dict with 5 model configs
- [ ] `load_ocr_config()` with missing `models` key raises `ConfigurationError`
- [ ] `load_ocr_config()` with model missing `enabled` defaults to `True`
- [ ] Extra fields in yaml model blocks are captured in `parameters` dict
- [ ] Unknown model names logged as warnings

---

## Test Plan

### File: `tests/test_config.py`

**Test `load_config`**:
1. `test_load_valid_config` — create temp TOML file with valid config, assert returned `AppConfig` fields match
2. `test_load_config_missing_file` — assert `ConfigurationError` raised for nonexistent path
3. `test_load_config_empty_file` — create empty temp file, assert `ConfigurationError`
4. `test_load_config_missing_openrouter` — TOML without `[openrouter]`, assert `ConfigurationError` mentions "openrouter"
5. `test_load_config_missing_api_key` — TOML with `[openrouter]` but no `api_key`, assert `ConfigurationError` mentions "api_key"
6. `test_load_config_invalid_api_key` — TOML with `api_key = "invalid"`, assert `ConfigurationError` mentions "sk-"
7. `test_load_config_missing_images_path` — TOML without `images_path`, assert `ConfigurationError`
8. `test_load_config_nonexistent_images_path_warns` — TOML with nonexistent path, assert logging.warning called
9. `test_load_config_default_base_url` — TOML without `base_url`, assert default value used
10. `test_load_config_default_model` — TOML without `default_model`, assert default value used

**Test `load_ocr_config`**:
11. `test_load_valid_ocr_config` — create temp YAML with 5 models, assert dict of 5 `ModelConfig`
12. `test_load_ocr_config_missing_file` — assert `ConfigurationError` for nonexistent path
13. `test_load_ocr_config_missing_models_key` — YAML without `models:`, assert `ConfigurationError`
14. `test_load_ocr_config_default_enabled` — model without `enabled` field, assert defaults to `True`
15. `test_load_ocr_config_extra_fields_in_parameters` — model with custom fields, assert they appear in `parameters`
16. `test_load_ocr_config_unknown_model_name` — YAML with extra model, assert warning logged

**Test schemas**:
17. `test_openrouter_config_valid` — construct with valid data, assert no error
18. `test_openrouter_config_invalid_api_key` — assert `ConfigurationError` for non-sk- prefix

Use `pytest` with `tmp_path` fixture for temp files. Use `caplog` for log assertion.

---

## Questions for Operator

None — all details are specified in PHASES.md and config files are straightforward.

---

## Dependencies on Other Stories

None — this is the foundational story. US-O1, US-O3, US-O4, US-O5, US-O7, US-O8 all depend on this story being complete.

---

## Estimated Complexity

**Medium** — straightforward parsing and validation, but careful error handling and edge cases add complexity.
