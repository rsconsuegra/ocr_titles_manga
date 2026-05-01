# Technical Debt

## Stuck-run sweeper

When a worker is OOM-killed (SIGKILL -9), the pipeline run stays in `"processing"` forever because the process dies instantly with no cleanup opportunity.

**Solution:** Add a periodic task (or API endpoint) that finds runs stuck in `"processing"` for longer than `time_limit` (15 min) and marks them as failed with `"Worker OOM or crashed"`.

**Location:** `ocr_manga_title/workers/ocr_worker.py` or a new `sweeper` module.

**Priority:** Medium. The pre-flight memory check (`_require_memory`) prevents most OOM scenarios, but doesn't catch memory exhaustion during model inference or from concurrent runs.

## Confidence field type mismatch

The LLM extractor assumes `confidence` is a numeric value (`float(normalized.get("confidence", 0.0))`) but custom prompts may instruct the LLM to return text labels like `"high"`, `"medium"`, `"low"`. This causes `ValueError: could not convert string to float: 'medium'` in `_build_result`.

**Location:** `ocr_manga_title/postprocess/llm_extractor.py:265` (`_build_result`)

**Solution options:**
- Add a `_normalize_confidence()` helper that maps string labels to floats (`high→0.9`, `medium→0.6`, `low→0.3`)
- Enforce in prompt instructions that `confidence` must be a float 0.0–1.0
- Validate confidence type in `ExtractedTitle` validator

**Priority:** Medium. The retry-without-JSON-mode fallback works, but any custom prompt returning non-numeric confidence will crash the extraction.

## LLM extraction strategy: `all_ocr` opt-in

The worker pipeline supports two strategies for feeding OCR results to the LLM:

- **`best_ocr`** (current default): Picks the highest-confidence OCR result and sends only that text to the LLM (1 call). Used by Quick Run, Playground, and Worker.
- **`all_ocr`**: Sends each OCR model's text to the LLM independently (N calls), then picks the best extraction. More thorough but N× cost and time.

The `all_ocr` strategy is implemented in `OCREngine._llm_extract_all()` but is **not yet exposed** via `PipelineProfile` or the frontend.

**To enable later:**
1. Add `llm_strategy` column to `pipeline_profiles` (VARCHAR(20), default `'best_ocr'`)
2. Alembic migration
3. Pass `strategy` param through `OCREngine._extract_titles()`
4. Frontend: profile editor dropdown

**Location:** `ocr_manga_title/engine/ocr_engine.py` (`_llm_extract_from_results`), `ocr_manga_title/services/ocr.py` (`pick_best_ocr`)

**Priority:** Low. `best_ocr` works well for typical use. `all_ocr` only helps when different OCR engines extract meaningfully different text that the LLM interprets differently.
