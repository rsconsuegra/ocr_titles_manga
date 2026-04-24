# US-1B2: Trigger Pipeline Execution

**Sub-phase**: 1B — FastAPI Application
**Depends on**: US-1B1 (upload creates pipeline_runs), US-1A1 (DB tables)
**Blocks**: US-1C1 (worker must have jobs to process)

---

## Overview

Create the pipeline route that enqueues a Dramatiq job for a given pipeline run. This is the trigger mechanism between the API and the async worker. The actual worker implementation is in US-1C1; this ticket only creates the API endpoint and broker configuration.

---

## Implementation Details

### 1. `ocr_manga_title/workers/__init__.py`

Empty init.

### 2. `ocr_manga_title/workers/broker.py`

```python
import os
import dramatiq
from dramatiq.brokers.redis import RedisBroker

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

broker = RedisBroker(url=redis_url)
dramatiq.set_broker(broker)
```

**Note**: Import this module before defining any actors. The broker must be set before `@dramatiq.actor` decorators are evaluated.

### 3. `ocr_manga_title/workers/ocr_worker.py` (stub — full impl in US-1C1)

For this ticket, create a minimal actor that the API can send messages to:

```python
import dramatiq
from ocr_manga_title.workers.broker import broker  # noqa: F401 — ensures broker is set

@dramatiq.actor(
    max_retries=3,
    min_backoff=10000,
    max_backoff=60000,
    time_limit=300000,
)
def process_pipeline_run(run_id: str):
    pass  # Implemented in US-1C1
```

### 4. `ocr_manga_title/api/routes/pipeline.py`

```python
import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas import PipelineRunResponse, PaginatedResponse
from ocr_manga_title.db.crud import get_pipeline_run, list_pipeline_runs

router = APIRouter()

@router.post("/run/{run_id}")
async def trigger_pipeline(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    run = await get_pipeline_run(session=db, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    if run.status != "pending":
        raise HTTPException(status_code=409, detail=f"Run already triggered (status: {run.status})")

    from ocr_manga_title.workers.ocr_worker import process_pipeline_run
    process_pipeline_run.send(str(run_id))

    return {"message": "Pipeline run enqueued", "run_id": str(run_id)}

@router.get("/runs", response_model=PaginatedResponse)
async def list_runs(
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    from ocr_manga_title.db.crud import count_pipeline_runs
    runs = await list_pipeline_runs(session=db, status=status, limit=limit, offset=offset)
    total = await count_pipeline_runs(session=db, status=status)
    return PaginatedResponse(
        items=[PipelineRunResponse.model_validate(r) for r in runs],
        total=total,
        limit=limit,
        offset=offset,
    )

@router.get("/runs/{run_id}")
async def get_run_detail(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from ocr_manga_title.db.crud import get_pipeline_run_detail
    run = await get_pipeline_run_detail(session=db, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return run
```

### 5. CRUD additions for `ocr_manga_title/db/crud.py`

```python
async def count_pipeline_runs(session: AsyncSession, status: str | None = None) -> int:
    from sqlalchemy import func as sa_func
    stmt = select(sa_func.count()).select_from(PipelineRun)
    if status:
        stmt = stmt.where(PipelineRun.status == status)
    result = await session.execute(stmt)
    return result.scalar_one()

async def get_pipeline_run_detail(session: AsyncSession, run_id: uuid.UUID) -> dict | None:
    from sqlalchemy.orm import selectinload
    stmt = (
        select(PipelineRun)
        .where(PipelineRun.id == run_id)
        .options(
            selectinload(PipelineRun.ocr_results).selectinload(OCRResult.post_processing_results)
        )
    )
    result = await session.execute(stmt)
    run = result.scalar_one_or_none()
    if not run:
        return None
    return {
        "id": run.id,
        "input_image_path": run.input_image_path,
        "status": run.status,
        "error_message": run.error_message,
        "created_at": run.created_at,
        "completed_at": run.completed_at,
        "ocr_results": [
            {
                "id": ocr.id,
                "model_name": ocr.model_name,
                "raw_text": ocr.raw_text,
                "confidence": ocr.confidence,
                "processing_time_ms": ocr.processing_time_ms,
                "error": ocr.error,
                "created_at": ocr.created_at,
                "post_processing_results": [
                    {
                        "id": pp.id,
                        "title_en": pp.title_en,
                        "title_ja": pp.title_ja,
                        "code": pp.code,
                        "confidence": pp.confidence,
                        "processing_type": pp.processing_type,
                        "created_at": pp.created_at,
                    }
                    for pp in ocr.post_processing_results
                ],
            }
            for ocr in run.ocr_results
        ],
    }
```

---

## Acceptance Criteria

- [ ] `POST /api/v1/pipeline/run/{run_id}` enqueues a Dramatiq message
- [ ] Returns 404 if run_id does not exist
- [ ] Returns 409 if run status is not "pending"
- [ ] Returns `{"message": "Pipeline run enqueued", "run_id": "..."}` on success
- [ ] `GET /api/v1/pipeline/runs` returns paginated list (US-1B3)
- [ ] `GET /api/v1/pipeline/runs/{run_id}` returns full details (US-1B4)
- [ ] Redis broker connects to `REDIS_URL` env var (default `redis://localhost:6379`)

---

## Test Specifications

**File**: `tests/test_api/test_pipeline.py`

Tests:
- `POST /api/v1/pipeline/run/{valid_pending_id}`: returns 200 with enqueue message
- `POST /api/v1/pipeline/run/{random_uuid}`: returns 404
- `POST /api/v1/pipeline/run/{completed_run_id}`: returns 409
- Verify `process_pipeline_run.send()` called with correct run_id (mock Dramatiq actor)
- `GET /api/v1/pipeline/runs`: returns paginated response with items and total
- `GET /api/v1/pipeline/runs?status=completed`: filters correctly
- `GET /api/v1/pipeline/runs?limit=5&offset=10`: paginates correctly

**Mocking strategy**: Mock `process_pipeline_run.send` to avoid needing Redis in tests. Verify it's called with the correct string run_id.
