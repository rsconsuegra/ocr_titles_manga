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
