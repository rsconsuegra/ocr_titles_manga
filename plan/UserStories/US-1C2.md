# US-1C2: Retry Failed Pipeline Runs

**Sub-phase**: 1C — Task Queue
**Depends on**: US-1C1 (worker actor implemented)
**Blocks**: None

---

## Overview

Configure and validate Dramatiq retry behavior for transient failures. The retry configuration is already set in the `@dramatiq.actor` decorator from US-1C1. This ticket validates that retries work correctly for different error types and that permanent errors are not retried.

---

## Implementation Details

### 1. Retry Configuration (already in US-1C1 decorator)

```python
@dramatiq.actor(
    max_retries=3,
    min_backoff=10000,    # 10s
    max_backoff=60000,    # 60s
    time_limit=300000,    # 5 min hard limit
)
```

This gives exponential backoff: ~10s, ~30s, ~60s between retries.

### 2. Error classification in `_process()`

The worker must distinguish between retryable and permanent errors:

```python
class RetryableError(Exception):
    """Transient errors that should be retried."""
    pass

class PermanentError(Exception):
    """Errors that should NOT be retried."""
    pass
```

**Retryable** (re-raise to trigger Dramatiq retry):
- LLM API errors (5xx, timeout, connection refused)
- Database connection errors
- Redis connection errors

**Permanent** (log and set status to "failed", do NOT re-raise):
- Image file not found
- Image file corrupt/unreadable
- Invalid run_id format
- Configuration errors

### 3. Error handling in worker

Update `_process()` from US-1C1:

```python
async def _process(run_id: str):
    ...
    try:
        ...
    except PermanentError as e:
        run.status = "failed"
        run.error_message = str(e)[:1000]
        run.completed_at = datetime.now(timezone.utc)
        await session.commit()
        logger.error(f"Pipeline run {run_id} failed permanently: {e}")
        # Do NOT re-raise — no retry
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)[:1000]
        run.completed_at = datetime.now(timezone.utc)
        await session.commit()
        logger.error(f"Pipeline run {run_id} failed (will retry): {e}")
        raise  # Re-raise to trigger Dramatiq retry
```

### 4. Specific error wrapping

```python
# In the _process function, after OCREngine.process():
image_path = Path(run.input_image_path)
if not image_path.exists():
    raise PermanentError(f"Image not found: {run.input_image_path}")
```

---

## Acceptance Criteria

- [ ] Transient errors (LLM timeout, DB connection) trigger retry up to 3 times
- [ ] Permanent errors (image not found) do NOT trigger retry
- [ ] After 3 retries exhausted, run status = "failed" with error_message
- [ ] Backoff is approximately 10s / 30s / 60s between retries
- [ ] Jobs older than 5 minutes are killed (time_limit=300000)
- [ ] Retry count logged in worker output
- [ ] Permanent errors set status to "failed" immediately (no retry)

---

## Test Specifications

**File**: `tests/test_worker/test_ocr_worker.py` (extend)

Tests:
- Mock `OCREngine.process` to raise `ConnectionError` (simulating LLM timeout): verify exception is re-raised (triggers retry)
- Mock to raise `FileNotFoundError` wrapped as `PermanentError`: verify NOT re-raised
- Mock to raise `TimeoutError`: verify re-raised (retry)
- After mock failure: verify run status = "failed", error_message populated
- Successful retry scenario: fail twice, succeed on third — verify status = "completed"

**Note**: Dramatiq retries happen at the framework level. In unit tests, we verify the error classification logic (re-raise vs. swallow). Integration retry testing requires a running Redis.
