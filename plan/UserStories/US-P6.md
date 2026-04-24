# US-P6: Engine Integration

**Phase**: P (Preprocessing) — Sub-phase PF  
**Priority**: Critical  
**Status**: Planned

---

## Story

> As an operator, I want the OCR engine to automatically preprocess images before running OCR models so that I get better extraction results without manually tuning each image.

---

## Scope

### In Scope
- Update `OCREngine.__init__()` to accept preprocessing config
- Update `OCREngine.process()` to run preprocessing pipeline
- Feed preprocessed image to OCR models
- Include `PreProcessResult` in `PipelineResult`
- Update `main.py` to load `preprocess.yaml`
- Backward compatibility: existing code works without preprocessing

### Out of Scope
- Individual preprocessing steps (US-P2 through US-P5)
- Notebook (US-P7)

---

## Preconditions

1. **US-P1 through US-P5 complete**: All preprocessing steps implemented and tested
2. **Phase 0 complete**: `OCREngine` working with all OCR models
3. All existing tests (106) passing

---

## Implementation Details

### File: `manga_ocr/engine.py` (updated)

```python
from manga_ocr.preprocess import PreProcessingPipeline

class OCREngine:
    def __init__(self, config: AppConfig, ocr_config: dict[str, ModelConfig], preprocess_config: dict | None = None):
        self._config = config
        self._ocr_config = ocr_config
        self._models = self._initialize_models()
        self._llm_extractor = LLMExtractor(config.openrouter)
        self._rule_matcher = RuleMatcher()
        self._preprocess_pipeline: PreProcessingPipeline | None = None

        if preprocess_config:
            pp_settings = preprocess_config.get("preprocessing", {})
            if pp_settings.get("enabled", False):
                self._preprocess_pipeline = PreProcessingPipeline(preprocess_config, config.images_path)
                logger.info("Preprocessing pipeline enabled")

        logger.info(f"OCREngine initialized with {len(self._models)} models: "
                     f"{[m.name for m in self._models]}")

    def process(self, image_path: str) -> PipelineResult:
        # 1. Validate image
        self._validate_image(image_path)

        # 2. Run preprocessing if enabled
        preprocess_result = None
        ocr_image_path = image_path

        if self._preprocess_pipeline:
            preprocess_result = self._preprocess_pipeline.process(image_path)
            if preprocess_result.output_path:
                ocr_image_path = preprocess_result.output_path
                logger.info(f"Using preprocessed image: {ocr_image_path}")
            else:
                logger.warning("Preprocessing produced no output, using original image")

        # 3. Run OCR models on (possibly preprocessed) image
        ocr_results = self._run_models(ocr_image_path)

        # 4. Post-process
        extracted, errors = self._post_process(ocr_results)

        # 5. Build result
        return PipelineResult(
            input_path=image_path,
            ocr_results=ocr_results,
            extracted=extracted,
            errors=errors,
            preprocess_result=preprocess_result,
        )
```

**Key design decisions**:
- `preprocess_config` parameter is optional — existing code passes `None`, preprocessing disabled
- If preprocessing fails (returns no output), fall back to original image (graceful degradation)
- `PipelineResult.input_path` always shows the **original** image path
- `PipelineResult.preprocess_result.output_path` shows the preprocessed image path

### File: `main.py` (updated)

```python
from manga_ocr.config import load_config, load_ocr_config, load_preprocess_config

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    config = load_config()
    ocr_config = load_ocr_config()
    preprocess_config = load_preprocess_config()

    engine = OCREngine(config, ocr_config, preprocess_config)

    try:
        result = engine.process(image_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))
```

---

## Postconditions

1. `OCREngine(config, ocr_config)` works as before (no preprocess_config = no preprocessing)
2. `OCREngine(config, ocr_config, preprocess_config)` runs preprocessing when enabled
3. `PipelineResult.preprocess_result` is `None` when preprocessing disabled
4. `PipelineResult.preprocess_result` contains step results when preprocessing enabled
5. OCR models receive preprocessed image when available, original otherwise
6. `main.py` loads `preprocess.yaml` automatically
7. All existing 106 tests pass without modification
8. JSON output from `main.py` includes `preprocess_result` field

---

## Validation Checklist

- [ ] Existing engine tests pass without modification (backward compatibility)
- [ ] Engine with preprocessing disabled behaves identically to before
- [ ] Engine with preprocessing enabled runs pipeline before OCR
- [ ] Preprocessing failure falls back to original image gracefully
- [ ] `PipelineResult.preprocess_result` is None when disabled
- [ ] `PipelineResult.preprocess_result` has step results when enabled
- [ ] `input_path` in result always shows original image path
- [ ] `main.py` loads `preprocess.yaml` and passes to engine
- [ ] `main.py` works without `preprocess.yaml` file present
- [ ] CLI test still passes (mocked OCREngine still works)

---

## Test Plan

### File: `tests/test_engine.py` (updated)

**New tests** (add to existing `TestOCREngineProcess` class):

1. `test_process_with_preprocessing_enabled` — mock PreProcessingPipeline, verify it's called, verify preprocess_result in output
2. `test_process_with_preprocessing_disabled` — no preprocess_config, verify preprocess_result is None
3. `test_process_preprocessing_failure_fallback` — mock pipeline returning no output_path, verify original image used
4. `test_process_preprocessing_provides_image_to_ocr` — mock pipeline returning output_path, verify OCR models receive preprocessed path
5. `test_process_preprocessing_result_in_pipeline_result` — verify full PreProcessResult structure in PipelineResult

### Backward compatibility:

6. All existing engine tests must pass without any changes to test code or engine constructor calls

Use `_make_engine()` helper — update to accept optional `preprocess_config` parameter (default `None`):

```python
def _make_engine(tmp_path, models_config=None, preprocess_config=None):
    # ... existing setup ...
    return OCREngine(config, models_config, preprocess_config)
```

---

## Questions for Operator

None.

---

## Dependencies

- **US-P1 through US-P5** all complete
- All Phase 0 tests passing

---

## Estimated Complexity

**Medium** — integration is straightforward, but ensuring backward compatibility and graceful degradation requires careful testing.
