# US-O8: Graceful Error Handling

**Phase**: 0 (OCR Engine) — Sub-phase 0D  
**Priority**: High  
**Status**: Planned

---

## Story

> As an operator, I want the pipeline to continue processing even if one OCR model or the LLM fails so that I get partial results rather than a complete failure.

---

## Scope

### In Scope
- `OCREngine.process()` wraps each model call in try/except
- Failed model results captured as `OCRResult` with error message
- LLM extraction failures logged and skipped
- Rule matcher runs even if LLM fails
- Best-result selection from partial results
- Processing time recorded even for failures
- All errors collected in `PipelineResult.errors`

### Out of Scope
- Retry logic for individual model failures (Phase 1 Dramatiq retries)
- Persistent error storage (Phase 1 database)
- Error notification/alerting
- Error classification (transient vs permanent)

---

## Preconditions

1. **US-O2 complete**: `OCRResult`, `PipelineResult`, `ExtractedTitle` schemas defined
2. **US-O3 complete**: `MangaOCRModel` implemented
3. **US-O4 complete**: `TesseractModel` implemented
4. **US-O5 complete**: `LLMExtractor` implemented
5. **US-O6 complete**: `RuleMatcher` implemented
6. **US-O7 complete**: `OCREngine` initializes models from config

---

## Implementation Details

### File: `manga_ocr/engine.py`

The `process()` method must implement the error handling matrix:

```python
def process(self, image_path: str) -> PipelineResult:
    errors: list[str] = []
    ocr_results: list[OCRResult] = []
    extracted_titles: list[ExtractedTitle] = []

    # 1. Validate image
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"}:
        raise ValueError(f"Unsupported image format: {path.suffix}")

    # 2. Run each enabled model
    for model in self._models:
        start = time.monotonic()
        try:
            result = model.run(image_path)
            ocr_results.append(result)
        except FileNotFoundError:
            raise  # re-raise, this is a caller error
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            ocr_results.append(OCRResult(
                raw_text="",
                model_name=model.name,
                confidence=0.0,
                processing_time_ms=elapsed_ms,
                error=str(e),
            ))
            errors.append(f"Model {model.name} failed: {e}")
            logger.error(f"Model {model.name} failed: {e}", exc_info=True)

    # 3. Post-process successful results
    for result in ocr_results:
        if result.error is not None or not result.raw_text.strip():
            continue

        # LLM extraction
        try:
            extracted = self._llm_extractor.extract(result.raw_text)
        except Exception as e:
            errors.append(f"LLM extraction failed for {result.model_name}: {e}")
            logger.error(f"LLM extraction failed for {result.model_name}: {e}")
            extracted = ExtractedTitle(confidence=0.0, source_model=result.model_name, source_method="llm_failed")

        # Rule-based augmentation
        try:
            extracted = self._rule_matcher.augment(extracted, result.raw_text)
        except Exception as e:
            errors.append(f"Rule matching failed for {result.model_name}: {e}")
            logger.error(f"Rule matching failed for {result.model_name}: {e}")

        extracted_titles.append(extracted)

    # 4. If LLM failed for all, try rules-only on raw text
    if not extracted_titles or all(t.confidence == 0.0 for t in extracted_titles):
        for result in ocr_results:
            if result.error is None and result.raw_text.strip():
                try:
                    rule_result = self._rule_matcher.match(result.raw_text)
                    if rule_result.code is not None:
                        rule_result.source_model = result.model_name
                        extracted_titles.append(rule_result)
                except Exception as e:
                    errors.append(f"Rule matching failed for {result.model_name}: {e}")

    # 5. Select best result
    best = None
    if extracted_titles:
        best = max(extracted_titles, key=lambda t: t.confidence)

    return PipelineResult(
        input_path=str(image_path),
        ocr_results=ocr_results,
        extracted=best,
        timestamp=datetime.now(),
        errors=errors,
    )
```

Key error handling decisions:
- `FileNotFoundError` for missing image is ALWAYS re-raised (caller error, not pipeline error)
- All other exceptions are caught and logged; pipeline continues
- Processing time is recorded even for failed model runs (measured before the try/except)
- `PipelineResult.errors` is a flat list of error message strings for simple consumption
- Each `OCRResult` that failed has its own `error` field with the specific error
- If ALL post-processing fails, we still return raw OCR results
- Rule matcher gets a second chance if LLM failed entirely (rules-only fallback)

---

## Postconditions

1. Single model failure does not prevent other models from running
2. `PipelineResult.ocr_results` contains entries for ALL models (successful + failed)
3. Failed `OCRResult` has `error` field populated with error message
4. LLM failure does not prevent rule matching
5. All models failing returns `PipelineResult` with empty/failed results and errors listed
6. Processing time is recorded for failed attempts
7. No unhandled exceptions from `process()` on valid image files (except `FileNotFoundError` for missing images)

---

## Validation Checklist

- [ ] One model raises `RuntimeError` -> other model still runs, result included
- [ ] All models raise -> `PipelineResult` with all errors, `extracted=None`
- [ ] LLM raises `APIError` -> rule matcher still runs on raw text
- [ ] LLM + rules both fail -> `extracted=None`, raw results still available
- [ ] `FileNotFoundError` for missing image -> re-raised (not caught)
- [ ] `ValueError` for unsupported format -> re-raised
- [ ] Processing time recorded for failed model (not 0, not missing)
- [ ] `PipelineResult.errors` list populated with all error messages
- [ ] Individual `OCRResult.error` populated for failed models
- [ ] Successful results have `OCRResult.error = None`

---

## Test Plan

### File: `tests/test_engine.py` (error handling tests)

Use mocks to simulate failures:

1. `test_process_one_model_fails_other_succeeds` — mock manga-ocr to raise, Tesseract succeeds, assert both OCRResults present (one with error, one with text)
2. `test_process_all_models_fail` — both mock raises, assert `PipelineResult` with 2 failed `OCRResult`s, `extracted=None`, errors list has 2 entries
3. `test_process_llm_fails_rules_succeed` — LLM mock raises, rule matcher finds ISBN in raw text, assert `extracted.code` populated
4. `test_process_llm_and_rules_both_fail` — both raise, assert `extracted=None`
5. `test_process_missing_image_raises_file_not_found` — nonexistent path, assert `FileNotFoundError` raised
6. `test_process_unsupported_format_raises_value_error` — `.txt` file, assert `ValueError`
7. `test_process_records_time_on_failure` — mock model to sleep then raise, assert `processing_time_ms > 0`
8. `test_process_errors_list_populated` — multiple failures, assert `PipelineResult.errors` contains all error messages
9. `test_process_rules_only_fallback` — LLM returns all nulls, rules find code in raw text, assert code in result
10. `test_process_no_exception_on_valid_image` — valid image, both models succeed, assert no errors

---

## Questions for Operator

None.

---

## Dependencies

- **US-O2** through **US-O7** all must be complete (this is the integration story)
- All model wrappers and post-processors implemented

---

## Estimated Complexity

**Medium-High** — the error handling matrix has many branches, each needs careful testing.
