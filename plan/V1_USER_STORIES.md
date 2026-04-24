# V1 User Stories: OCR Engine Module

These user stories cover the standalone OCR engine package (Phase 0). There is no UI — all interaction is via Python code, notebooks, or CLI.

---

## US-O1: Process a Manga Image End-to-End

> As an operator, I want to pass an image file path to the OCR engine and receive a structured result containing the manga title (EN/JA), code, and confidence score so that I can extract manga references without manual transcription.

**Acceptance Criteria**:
- Calling `OCREngine(config).process("path/to/image.png")` returns a `PipelineResult`
- `PipelineResult` contains at least one `OCRResult` from each enabled model
- `PipelineResult.extracted` contains `ExtractedTitle` with title_en, title_ja, code, and confidence
- Processing completes within 30 seconds for a single image
- No unhandled exceptions on valid image files (PNG, JPG, WEBP)

---

## US-O2: Load Configuration from Files

> As an operator, I want the engine to read its settings from `configs.toml` and `ocrs.yaml` so that I can change OCR models, LLM provider, and parameters without editing source code.

**Acceptance Criteria**:
- `load_config()` reads `configs.toml` and returns `AppConfig` with OpenRouter settings and paths
- `load_ocr_config()` reads `ocrs.yaml` and returns a list of `ModelConfig` with enabled flags
- Missing required fields (e.g., `openrouter.api_key`) raise a clear `ConfigurationError` with the field name
- Optional fields have sensible defaults (e.g., `openrouter.base_url` defaults to `"https://openrouter.ai/api/v1"`)
- Extra/unknown fields in config files are ignored without error

---

## US-O3: Run manga-ocr on Japanese Text

> As an operator, I want to use the manga-ocr model to extract Japanese text from manga panel images so that I get specialized recognition for manga-specific text (speech bubbles, overlays, stylized fonts).

**Acceptance Criteria**:
- `MangaOCRModel.run("manga_panel.png")` returns `OCRResult` with `model_name="manga-ocr"`
- Raw text contains recognizable Japanese characters (hiragana, katakana, kanji)
- Model weights are downloaded automatically on first use from HuggingFace
- Subsequent calls reuse the loaded model (no re-download)
- Returns empty `raw_text` and low confidence if the image contains no text

---

## US-O4: Run Tesseract on English and Japanese Text

> As an operator, I want to use Tesseract as a general-purpose OCR fallback that handles both English and Japanese so that I have a baseline comparison for manga-ocr results.

**Acceptance Criteria**:
- `TesseractModel.run("image.png")` returns `OCRResult` with `model_name="tesseract"`
- Configured with both English and Japanese language packs
- Language settings come from `ocrs.yaml` (configurable per-model)
- PSM and OEM modes configurable via `ocrs.yaml` parameters
- Returns processing time in milliseconds

---

## US-O5: Extract Structured Data via LLM

> As an operator, I want raw OCR text to be sent to an LLM (via OpenRouter) that extracts the manga title (English and Japanese), codes, and ISBNs so that I get clean, structured data instead of noisy raw text.

**Acceptance Criteria**:
- `LLMExtractor.extract("raw ocr text...")` returns `ExtractedTitle` with title_en, title_ja, code, confidence
- LLM model ID comes from `configs.toml` (`openrouter.default_model`)
- Prompt loaded from `prompts/llm/extract_title_v1.md`
- API key read from `configs.toml` (`openrouter.api_key`)
- If LLM returns invalid JSON, the extractor returns `ExtractedTitle` with `confidence=0.0` and the error logged
- If OpenRouter API is unreachable, returns partial result without crashing

---

## US-O6: Detect ISBN and Codes via Rules

> As an operator, I want the rule-based matcher to detect ISBN-10, ISBN-13, and other common manga code patterns from raw text so that codes are extracted even when the LLM misses them.

**Acceptance Criteria**:
- `RuleMatcher.match("ISBN 4-06-319310-6 ...")` detects ISBN-10
- `RuleMatcher.match("978-4-06-319310-8 ...")` detects ISBN-13
- Title normalization strips extra whitespace and normalizes punctuation
- Can augment an existing `ExtractedTitle` (fills in fields the LLM missed)
- Regex patterns are defined in code (no external config needed for v1)

---

## US-O7: Enable and Disable OCR Models

> As an operator, I want to enable or disable individual OCR models via `ocrs.yaml` so that I control which models run in the pipeline without code changes.

**Acceptance Criteria**:
- Setting `enabled: false` in `ocrs.yaml` for a model excludes it from pipeline execution
- Setting `enabled: true` includes the model if it is implemented (not a stub)
- Stubs (`paddle`, `easyocr`, `glm_ocr`) are always unavailable regardless of `enabled` flag
- `OCREngine` logs which models are enabled/available at startup

---

## US-O8: Graceful Error Handling

> As an operator, I want the pipeline to continue processing even if one OCR model or the LLM fails so that I get partial results rather than a complete failure.

**Acceptance Criteria**:
- If one OCR model raises an exception, the pipeline logs the error and continues with remaining models
- `PipelineResult` includes all successful `OCRResult`s, even if some models failed
- If all OCR models fail, `PipelineResult` has empty `ocr_results` and `extracted=None`
- If the LLM call fails, rule-based matching still runs on raw text
- Processing time is recorded per model, even for failed attempts

---

## US-O9: Test the Pipeline Interactively

> As an operator, I want a Jupyter notebook where I can load images, run individual models, compare outputs, and test the full pipeline so that I can experiment with configuration and evaluate results visually.

**Acceptance Criteria**:
- Notebook `01_ocr_testing.ipynb` exists in `notebooks/`
- Notebook cells demonstrate: config loading, running manga-ocr, running Tesseract, running LLM extraction, running full pipeline
- Results displayed inline (text output, confidence scores)
- Works with any image placed in the configured `images_path`

---

## US-O10: Validate with Unit Tests

> As an operator, I want a test suite that verifies each component works correctly so that I can refactor and add features with confidence.

**Acceptance Criteria**:
- `make test` runs all tests with pytest and exits 0
- Tests cover: config loading, schema validation, model interface, LLM extractor (mocked), rule matcher, engine integration
- No tests require actual API calls (LLM tests use mocks)
- No tests require real images (OCR model tests use mocks or tiny test fixtures)
- Test coverage >= 80% for `manga_ocr/` package
