import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.pipeline import (
    PaginatedResponse,
    PipelineActionResponse,
    PipelineRunDetailResponse,
    PipelineRunResponse,
)
from ocr_manga_title.db.crud import (
    count_pipeline_runs,
    get_pipeline_run,
    get_pipeline_run_detail,
    list_pipeline_runs,
    update_batch_progress,
)
from ocr_manga_title.db.enums import RunStatus
from ocr_manga_title.db.models import OCRResult

router = APIRouter()

_RETRYABLE_STATUSES = {s.value for s in RunStatus} - {RunStatus.PROCESSING}
_CANCELABLE_STATUSES = {RunStatus.PENDING, RunStatus.PROCESSING}


@router.post("/run/{run_id}", response_model=PipelineActionResponse)
async def trigger_pipeline(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Enqueue a pending, failed, completed, or cancelled pipeline run for processing."""
    run = await get_pipeline_run(session=db, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found"
        )
    if run.status not in _RETRYABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run cannot be retried (status: {run.status})",
        )

    if run.status != RunStatus.PENDING:
        run.status = RunStatus.PENDING
        run.error_message = None
        run.completed_at = None
        await db.execute(delete(OCRResult).where(OCRResult.pipeline_run_id == run.id))
        if run.batch_run_id:
            await update_batch_progress(db, run.batch_run_id)

    from ocr_manga_title.workers.ocr_worker import process_pipeline_run

    process_pipeline_run.send(str(run_id))

    return PipelineActionResponse(message="Pipeline run enqueued", run_id=str(run_id))


@router.post("/runs/{run_id}/cancel", response_model=PipelineActionResponse)
async def cancel_pipeline_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending or processing pipeline run."""
    from ocr_manga_title.schemas import utcnow

    run = await get_pipeline_run(session=db, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found"
        )
    if run.status not in _CANCELABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run cannot be cancelled (status: {run.status})",
        )

    run.status = RunStatus.CANCELLED
    run.completed_at = utcnow()
    if run.batch_run_id:
        await update_batch_progress(db, run.batch_run_id)

    return PipelineActionResponse(message="Pipeline run cancelled", run_id=str(run_id))


@router.get("/runs", response_model=PaginatedResponse[PipelineRunResponse])
async def list_runs(
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List pipeline runs with optional status filtering and pagination."""
    runs = await list_pipeline_runs(
        session=db, status=status, limit=limit, offset=offset
    )
    total = await count_pipeline_runs(session=db, status=status)
    return PaginatedResponse(
        items=[PipelineRunResponse.model_validate(r) for r in runs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/runs/{run_id}", response_model=PipelineRunDetailResponse)
async def get_run_detail(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve a pipeline run with its OCR and post-processing results."""
    run = await get_pipeline_run_detail(session=db, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found"
        )
    return PipelineRunDetailResponse.model_validate(run)


_MEDIA_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


@router.get("/runs/{run_id}/image")
async def get_run_image(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Serve the original input image for a pipeline run."""
    run = await get_pipeline_run(session=db, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found"
        )
    image_path = Path(run.input_image_path)
    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image file not found"
        )
    media_type = _MEDIA_TYPES.get(image_path.suffix.lower(), "application/octet-stream")
    return FileResponse(str(image_path), media_type=media_type, filename=image_path.name)
