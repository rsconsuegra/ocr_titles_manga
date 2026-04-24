# US-O1: Process a Manga Image End-to-End

**Phase**: 0 (OCR Engine) — Sub-phase 0D  
**Priority**: Critical  
**Status**: Planned

---

## Story

> As an operator, I want to pass an image file path to the OCR engine and receive a structured result containing the manga title (EN/JA), code, and confidence score so that I can extract manga references without manual transcription.

---

## Scope

### In Scope
- `OCREngine` class in `manga_ocr/engine.py`
- `process(image_path: str) -> PipelineResult` method
- Full pipeline: image validation -> OCR models -> LLM extraction -> rule matching -> best result selection
- Image format validation (PNG, JPG, WEBP, TIFF, BMP)
- Best result selection (highest confidence across all extractions)
- Timestamp recording

### Out of Scope
- Async processing (Phase 1 Dramatiq)
- Progress callbacks or streaming (Phase 4 WebSocket)
- Image preprocessing (resizing, rotation, contrast)
- Batch processing API (notebook only in Phase 0)
- Persistent storage of results (Phase 1 database)

---

## Preconditions

1. **US-O2 complete**: `AppConfig`, `ModelConfig`, `OCRResult`, `ExtractedTitle`, `PipelineResult` schemas defined; `load_config()` and `load_ocr_config()` working
2. **US-O3 complete**: `MangaOCRModel` implemented and returning `OCRResult`
3. **US-O4 complete**: `TesseractModel` implemented and returning `OCRResult`
4. **US-O5 complete**: `LLMExtractor` implemented and returning `ExtractedTitle`
5. **US-O6 complete**: `RuleMatcher` implemented with `match()` and `augment()`
6. **US-O7 complete**: `OCREngine` initializes enabled/available models from config
7. **US-O8 complete**: error handling matrix implemented in `process()`
8. Valid image file exists at the given path
9. Config files (`configs.toml`, `ocrs.yaml`) properly configured

---

## Implementation Details

### File: `manga_ocr/engine.py`

This is the integration point that ties all components together. By the time this story is fully validated, the engine must:

```python
class OCREngine:
    SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp", ".tif"}

    def __init__(self, config: AppConfig, ocr_config: dict[str, ModelConfig]):
        self._config = config
        self._ocr_config = ocr_config
        self._models = self._initialize_models()
        self._llm_extractor = LLMExtractor(config.openrouter)
        self._rule_matcher = RuleMatcher()
        logger.info(f"OCREngine initialized with {len(self._models)} models: "
                     f"{[m.name for m in self._models]}")

    def _initialize_models(self) -> list[BaseOCRModel]:
        """See US-O7 for full implementation details."""

    def process(self, image_path: str) -> PipelineResult:
        """See US-O8 for full error handling implementation."""
```

The `process()` method is the primary integration test point. It must:
1. Validate the image (exists, supported format)
2. Run all enabled/available OCR models
3. Post-process each successful OCR result (LLM + rules)
4. Select the best extraction
5. Return `PipelineResult`

### File: `main.py` (CLI entry point)

```python
import sys
import json
from manga_ocr.config import load_config, load_ocr_config
from manga_ocr.engine import OCREngine


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    config = load_config()
    ocr_config = load_ocr_config()

    engine = OCREngine(config, ocr_config)
    result = engine.process(image_path)

    print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    main()
```

---

## Postconditions

1. `OCREngine(config, ocr_config).process("path/to/image.png")` returns a `PipelineResult`
2. `PipelineResult.ocr_results` contains at least one `OCRResult` from each enabled model
3. `PipelineResult.extracted` is an `ExtractedTitle` or `None` (if nothing extracted)
4. When extraction succeeds, `ExtractedTitle` has `title_en`, `title_ja`, `code`, and `confidence`
5. Processing completes within 30 seconds for a single image
6. No unhandled exceptions on valid image files
7. `python main.py image.png` prints JSON result to stdout and exits 0
8. `python main.py nonexistent.png` exits 1 with error message

---

## Validation Checklist

- [ ] `process("valid_manga_image.png")` returns `PipelineResult` with `ocr_results` from enabled models
- [ ] `PipelineResult.extracted` has non-None fields when manga text is present
- [ ] `PipelineResult.timestamp` is set to current time
- [ ] Processing completes within 30 seconds
- [ ] PNG, JPG, WEBP images accepted
- [ ] `process("nonexistent.png")` raises `FileNotFoundError`
- [ ] `process("document.txt")` raises `ValueError` (unsupported format)
- [ ] `python main.py image.png` prints valid JSON
- [ ] `python main.py` (no args) prints usage and exits 1

---

## Test Plan

### File: `tests/test_engine.py` (integration tests)

These tests verify the full pipeline works end-to-end with mocked components:

1. `test_process_returns_pipeline_result` — mock all models and LLM, assert `PipelineResult` structure with all expected fields
2. `test_process_runs_all_enabled_models` — mock 2 models, verify both `run()` called
3. `test_process_runs_llm_on_each_result` — verify `LLMExtractor.extract()` called once per successful OCR result
4. `test_process_runs_rules_on_each_result` — verify `RuleMatcher.augment()` called once per successful OCR result
5. `test_process_selects_best_confidence` — mock 2 models returning different confidences, assert highest selected
6. `test_process_image_not_found_raises` — nonexistent path -> `FileNotFoundError`
7. `test_process_unsupported_format_raises` — `.txt` file -> `ValueError`
8. `test_process_no_text_extracted` — mock models returning empty text, assert `extracted=None` or low confidence
9. `test_process_single_model` — disable one model in config, verify only one `OCRResult`

### File: `tests/test_cli.py` (or in test_engine.py)

10. `test_main_with_valid_image` — mock `OCREngine.process()`, verify JSON output
11. `test_main_no_args_exits_1` — no CLI args, verify exit code 1
12. `test_main_nonexistent_image_exits_1` — bad path, verify exit code 1

---

## Questions for Operator

None.

---

## Dependencies

- **ALL other US-O stories** must be complete before this can be fully validated
- This story is both an implementation story (the engine itself) and an integration validation story

---

## Estimated Complexity

**Medium** — the engine code itself is moderate, but this story validates the entire pipeline works together.
