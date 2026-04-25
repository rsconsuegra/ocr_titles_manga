# Technical Debt

## Stuck-run sweeper

When a worker is OOM-killed (SIGKILL -9), the pipeline run stays in `"processing"` forever because the process dies instantly with no cleanup opportunity.

**Solution:** Add a periodic task (or API endpoint) that finds runs stuck in `"processing"` for longer than `time_limit` (15 min) and marks them as failed with `"Worker OOM or crashed"`.

**Location:** `ocr_manga_title/workers/ocr_worker.py` or a new `sweeper` module.

**Priority:** Medium. The pre-flight memory check (`_require_memory`) prevents most OOM scenarios, but doesn't catch memory exhaustion during model inference or from concurrent runs.
