# US-O10: Validate with Unit Tests

**Phase**: 0 (OCR Engine) — Sub-phase 0E  
**Priority**: High  
**Status**: Planned

---

## Story

> As an operator, I want a test suite that verifies each component works correctly so that I can refactor and add features with confidence.

---

## Scope

### In Scope
- pytest test suite in `tests/` directory
- Tests for: config, schemas, models, postprocessing, engine
- All external dependencies mocked (no real API calls, no real model weights)
- `make test` runs the full suite
- `make lint` passes with no errors
- Coverage target >= 80% for `manga_ocr/` package
- pytest configuration in `pyproject.toml`

### Out of Scope
- Integration tests with real models (manual testing via notebook)
- Performance benchmarks
- Coverage enforcement (CI gate) — no CI yet
- Test fixtures that require real manga images

---

## Preconditions

1. **US-O2 through US-O8 complete**: all components implemented
2. `pyproject.toml` has `pytest` in dev dependencies
3. All source files in `manga_ocr/` are importable

---

## Implementation Details

### pytest Configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
```

### Test File Structure

```
tests/
  __init__.py
  conftest.py              # shared fixtures
  test_config.py           # US-O2 tests
  test_schemas.py          # US-O2 schema tests
  test_models.py           # US-O3, US-O4, stubs
  test_postprocess.py      # US-O5, US-O6
  test_engine.py           # US-O1, US-O7, US-O8
```

### File: `tests/conftest.py`

Shared fixtures:

```python
import pytest
from pathlib import Path
from PIL import Image


@pytest.fixture
def valid_configs_toml(tmp_path):
    """Create a valid configs.toml in tmp_path."""
    toml_content = '''
images_path = "{images_path}"

[openrouter]
api_key = "sk-or-test-key-12345"
default_model = "google/gemini-2.5-flash"
base_url = "https://openrouter.ai/api/v1"
'''.format(images_path=str(tmp_path / "images"))
    config_file = tmp_path / "configs.toml"
    config_file.write_text(toml_content)
    (tmp_path / "images").mkdir()
    return config_file


@pytest.fixture
def valid_ocrs_yaml(tmp_path):
    """Create a valid ocrs.yaml in tmp_path."""
    yaml_content = '''
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
'''
    yaml_file = tmp_path / "ocrs.yaml"
    yaml_file.write_text(yaml_content)
    return yaml_file


@pytest.fixture
def blank_image(tmp_path):
    """Create a minimal 1x1 white PNG for testing."""
    img = Image.new("RGB", (1, 1), "white")
    path = tmp_path / "blank.png"
    img.save(path)
    return str(path)


@pytest.fixture
def sample_text_with_isbn():
    return "One Piece ワンピース ISBN 978-4-08-872509-4"


@pytest.fixture
def sample_ocr_result():
    from manga_ocr.schemas import OCRResult
    return OCRResult(
        raw_text="ワンピース One Piece ISBN 978-4-08-872509-4",
        model_name="manga-ocr",
        confidence=0.7,
        processing_time_ms=150,
    )
```

### File: `tests/test_config.py`

Tests for `load_config()` and `load_ocr_config()` (as detailed in US-O2 test plan).

### File: `tests/test_schemas.py`

Tests for Pydantic model validation:

1. `test_ocr_result_valid` — construct with all fields, assert no error
2. `test_ocr_result_minimal` — construct with only required fields (raw_text, model_name, confidence, processing_time_ms), assert defaults for optional fields
3. `test_ocr_result_confidence_range` — confidence 0.0, 0.5, 1.0 all valid; test edge cases
4. `test_extracted_title_all_none` — construct with all None, assert valid
5. `test_extracted_title_all_populated` — all fields filled, assert valid
6. `test_pipeline_result_serialization` — construct and verify `.model_dump_json()` works
7. `test_pipeline_result_deserialization` — create from dict, verify fields
8. `test_app_config_missing_openrouter` — assert validation error
9. `test_model_config_defaults` — missing enabled/language/parameters, assert defaults
10. `test_openrouter_config_api_key_validation` — non-sk- prefix raises error

### File: `tests/test_models.py`

Tests for all model classes (as detailed in US-O3 and US-O4 test plans):

- `BaseOCRModel` is abstract — verify it cannot be instantiated
- `MangaOCRModel` tests (mocked)
- `TesseractModel` tests (mocked)
- `PaddleModel`, `EasyOCRModel`, `GLMOCRModel` stub tests
- Model interface compliance tests (all implement `name`, `is_available`, `run()`)

### File: `tests/test_postprocess.py`

Tests for LLM extractor and rule matcher (as detailed in US-O5 and US-O6 test plans).

### File: `tests/test_engine.py`

Tests for pipeline orchestrator (as detailed in US-O1, US-O7, US-O8 test plans).

### Makefile Targets

Update `Makefile`:

```makefile
.PHONY: test lint run setup notebook

setup:
	uv sync

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .
	uv run ruff format --check .

run:
	uv run python main.py

notebook:
	uv run jupyter notebook notebooks/
```

---

## Postconditions

1. `make test` exits with code 0 (all tests pass)
2. `make lint` exits with code 0 (no lint errors)
3. Test files cover all components: config, schemas, models, postprocess, engine
4. No test requires real API calls, real model weights, or real images
5. Coverage for `manga_ocr/` package >= 80%
6. Each test file is independent (no ordering dependencies)

---

## Validation Checklist

- [ ] `make test` runs all tests and exits 0
- [ ] `make lint` passes with no errors
- [ ] `tests/test_config.py` covers config loading edge cases
- [ ] `tests/test_schemas.py` covers Pydantic validation
- [ ] `tests/test_models.py` covers all 5 model classes
- [ ] `tests/test_postprocess.py` covers LLM extractor and rule matcher
- [ ] `tests/test_engine.py` covers pipeline orchestration and error handling
- [ ] No test makes real API calls (all mocked)
- [ ] No test requires real image files (uses fixtures or mocks)
- [ ] `conftest.py` provides shared fixtures
- [ ] `pytest` configuration in `pyproject.toml`

---

## Test Plan

This IS the test plan — meta-story. Verify by running:

```bash
make test
make lint
```

Both must exit 0.

---

## Questions for Operator

None.

---

## Dependencies

- **US-O2 through US-O8** all complete
- `pytest` in dev dependencies
- `Makefile` updated

---

## Estimated Complexity

**Medium** — individual tests are simple, but there are many of them across all components. The `conftest.py` fixtures need to be reusable and clean.
