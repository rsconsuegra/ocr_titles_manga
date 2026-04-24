# V1 Plan: OCR Engine Module

**Phase**: 0 (Standalone OCR Engine)  
**Scope**: Python package only — no API server, no frontend, no database  
**Goal**: Working OCR pipeline that processes an image and returns structured manga title data  

---

## What We Are Building

A standalone Python package (`manga_ocr/`) that:
1. Loads configuration from `configs.toml` and `ocrs.yaml`
2. Accepts an image file path as input
3. Runs enabled OCR models against the image
4. Sends raw OCR text to an OpenRouter LLM for cleanup and extraction
5. Applies rule-based matching for ISBN and code patterns
6. Returns a structured result with manga title (EN/JA), code, and confidence score

## What We Are NOT Building (Yet)

- No FastAPI server or REST endpoints
- No React frontend
- No PostgreSQL database
- No Dramatiq/Redis task queue
- No Agenta.ai integration (prompts loaded from local files only)
- No social media URL fetching
- PaddleOCR, EasyOCR, and GLM OCR are stubs only

---

## Target Directory Structure

```
manga_ocr/
  manga_ocr/                    # Python package
    __init__.py
    config.py                   # Config loader (TOML + YAML)
    schemas.py                  # Pydantic data models
    engine.py                   # Pipeline orchestrator
    models/
      __init__.py
      base.py                   # Abstract OCR model interface
      manga_ocr_model.py        # manga-ocr wrapper (working)
      tesseract_model.py        # Tesseract wrapper (working)
      paddle_model.py           # PaddleOCR wrapper (stub)
      easyocr_model.py          # EasyOCR wrapper (stub)
      glm_ocr_model.py          # GLM OCR wrapper (stub)
    postprocess/
      __init__.py
      llm_extractor.py          # OpenRouter LLM client
      rule_matcher.py           # Regex/rule-based matching
  prompts/
    ocr/
      manga_ocr_v1.md           # OCR model prompt (if applicable)
    llm/
      extract_title_v1.md       # LLM extraction prompt
  tests/
    __init__.py
    test_config.py
    test_schemas.py
    test_models.py
    test_postprocess.py
    test_engine.py
  configs.toml                  # App config (OpenRouter key, paths)
  ocrs.yaml                     # OCR model configs
  notebooks/
    01_ocr_testing.ipynb        # Interactive testing
  pyproject.toml                # Dependencies
  Makefile                      # run, test, lint targets
```

---

## Implementation Steps

### Step 1: Project Setup

**Task**: Update `pyproject.toml` with dependencies and create package structure.

**Dependencies to add**:
```
manga-ocr
pytesseract
openai
pydantic>=2.0
pyyaml
tomli
pillow
```

**Dev dependencies**:
```
pytest
jupyter
```

**Files created**:
- `manga_ocr/__init__.py`
- `manga_ocr/models/__init__.py`
- `manga_ocr/postprocess/__init__.py`
- `tests/__init__.py`

### Step 2: Config Loader

**Task**: `manga_ocr/config.py` — load and validate configuration files.

**Behavior**:
- Read `configs.toml` for: OpenRouter API key, default model ID, base URL, image paths
- Read `ocrs.yaml` for: per-model config (enabled flag, language, parameters)
- Return typed Pydantic config objects
- Fail fast with clear error messages if required config is missing

### Step 3: Pydantic Schemas

**Task**: `manga_ocr/schemas.py` — define all data types used in the pipeline.

**Models**:
- `OCRResult`: raw_text, model_name, confidence (0.0-1.0), processing_time_ms
- `ExtractedTitle`: title_en, title_ja, code, confidence, source_model
- `PipelineResult`: input_path, ocr_results (list), extracted (optional), timestamp
- `ModelConfig`: name, enabled, language, parameters
- `AppConfig`: openrouter settings, paths

### Step 4: Base OCR Model Interface

**Task**: `manga_ocr/models/base.py` — abstract base class for all OCR models.

**Interface**:
- `name: str` — model identifier
- `is_available: bool` — whether the model can be used
- `run(image_path: str) -> OCRResult` — execute OCR on an image

### Step 5: manga-ocr Wrapper

**Task**: `manga_ocr/models/manga_ocr_model.py` — wrap the HuggingFace manga-ocr model.

**Behavior**:
- Load `kha-white/manga-ocr-simplified` on first use (lazy loading)
- Accept image path, preprocess if needed, run inference
- Return `OCRResult` with raw text, model name "manga-ocr", estimated confidence
- Handle model download on first run

### Step 6: Tesseract Wrapper

**Task**: `manga_ocr/models/tesseract_model.py` — wrap pytesseract.

**Behavior**:
- Configure with Japanese + English language pack
- Accept image path, run OCR, return `OCRResult`
- Configurable via `ocrs.yaml` parameters (PSM mode, OEM mode, etc.)

### Step 7: Model Stubs

**Task**: Create stub implementations for remaining models.

**Files**:
- `manga_ocr/models/paddle_model.py`
- `manga_ocr/models/easyocr_model.py`
- `manga_ocr/models/glm_ocr_model.py`

**Behavior**:
- `is_available` returns `False`
- `run()` raises `NotImplementedError` with message like "PaddleOCR integration not yet implemented"
- Structured so future implementation just needs to fill in `run()` and flip `is_available`

### Step 8: LLM Extractor

**Task**: `manga_ocr/postprocess/llm_extractor.py` — send raw OCR text to OpenRouter for cleanup.

**Behavior**:
- Use OpenAI Python SDK with `base_url="https://openrouter.ai/api/v1"`
- Model ID loaded from `configs.toml` (not hardcoded)
- Prompt loaded from `prompts/llm/extract_title_v1.md`
- Input: raw OCR text string
- Output: `ExtractedTitle` parsed from LLM JSON response
- Handle API errors gracefully (return partial result with low confidence)

### Step 9: Rule-Based Matcher

**Task**: `manga_ocr/postprocess/rule_matcher.py` — regex and pattern matching.

**Patterns to detect**:
- ISBN-10: `\d{1,5}[- ]?\d{1,7}[- ]?\d{1,7}[- ]?[\dX]`
- ISBN-13: `\d{3}[- ]?\d{1,5}[- ]?\d{1,7}[- ]?\d{1,7}[- ]?\d`
- Manga-specific codes (configurable patterns)
- Title normalization: strip whitespace, normalize punctuation

**Behavior**:
- Input: raw text or `ExtractedTitle`
- Output: `ExtractedTitle` with any additional codes found, normalized titles
- Can run standalone or augment LLM results

### Step 10: Pipeline Orchestrator

**Task**: `manga_ocr/engine.py` — coordinate the full pipeline.

**Class `OCREngine`**:
- Constructor takes config, initializes enabled models + post-processors
- `process(image_path: str) -> PipelineResult`:
  1. Validate image exists
  2. Run each enabled OCR model (sequentially to manage memory)
  3. Collect all `OCRResult`s
  4. Run LLM extractor on each result
  5. Run rule matcher
  6. Aggregate best result (highest confidence)
  7. Return `PipelineResult`

### Step 11: LLM Prompt File

**Task**: `prompts/llm/extract_title_v1.md` — initial extraction prompt.

**Purpose**: Instruct the LLM to extract manga title (EN), manga title (JA), and any codes/ISBNs from raw OCR text. Must handle noisy input, partial text, and mixed languages.

### Step 12: Tests

**Task**: Unit and integration tests for all components.

**Test files**:
- `tests/test_config.py` — config loading, missing file handling, validation
- `tests/test_schemas.py` — Pydantic model validation
- `tests/test_models.py` — model interface compliance, stub behavior
- `tests/test_postprocess.py` — LLM extractor (mocked API), rule matcher (unit)
- `tests/test_engine.py` — full pipeline (mocked models and LLM)

### Step 13: Makefile Targets

**Task**: Update `Makefile` with convenience commands.

**Targets**:
- `make run` — run `main.py` with a sample image
- `make test` — run pytest
- `make lint` — run ruff check + format
- `make notebook` — launch Jupyter

### Step 14: Interactive Notebook

**Task**: `notebooks/01_ocr_testing.ipynb` — manual testing notebook.

**Contents**:
- Load config
- Run individual OCR models on sample images
- Compare outputs
- Run full pipeline
- Display results

---

## Configuration Files

### `configs.toml`

```toml
images_path = "/Users/rconsuegra/Pictures"

[openrouter]
api_key = "sk-or-..."
default_model = "google/gemini-2.5-flash"
base_url = "https://openrouter.ai/api/v1"
```

### `ocrs.yaml`

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

## Acceptance Criteria for V1

- [ ] `manga_ocr` package imports without errors
- [ ] Config loader reads `configs.toml` and `ocrs.yaml`, returns typed objects
- [ ] manga-ocr wrapper processes a manga panel image and returns Japanese text
- [ ] Tesseract wrapper processes an image and returns EN/JA text
- [ ] LLM extractor sends raw text to OpenRouter and returns `ExtractedTitle`
- [ ] Rule matcher detects ISBN-10, ISBN-13 patterns from raw text
- [ ] Pipeline orchestrator runs end-to-end: image -> OCR -> LLM -> rules -> result
- [ ] All tests pass (`make test`)
- [ ] No lint errors (`make lint`)
- [ ] Notebook demonstrates full pipeline on sample images
