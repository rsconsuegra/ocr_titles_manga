import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.batch import BatchRunDetailResponse, BatchRunResponse
from ocr_manga_title.api.schemas.pipeline import (
    PaginatedResponse,
    PipelineRunResponse,
)
from ocr_manga_title.db.crud import (
    count_batch_runs,
    create_batch_run,
    create_pipeline_run,
    get_batch_run,
    list_batch_runs,
)
from ocr_manga_title.db.enums import BatchStatus, RunStatus
from ocr_manga_title.db.models import BatchRun
from ocr_manga_title.services.config import build_run_config_snapshot
from ocr_manga_title.settings import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, MAX_FILES, UPLOAD_DIR
from ocr_manga_title.workers.ocr_worker import process_pipeline_run

router = APIRouter()

_UPLOAD_DIR = Path(UPLOAD_DIR)


async def _save_uploaded_files(
    files: list[UploadFile],
    batch_id: uuid.UUID,
    db: AsyncSession,
    config_snapshot: dict | None,
) -> list:
    runs = []
    for file in files:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large: {file.filename} (max 20MB)",
            )

        file_id = uuid.uuid4()
        save_path = _UPLOAD_DIR / f"{file_id}{ext}"
        save_path.write_bytes(content)

        run = await create_pipeline_run(
            session=db,
            input_image_path=str(save_path),
            source_platform="manual",
            batch_run_id=batch_id,
            preprocess_config=config_snapshot,
        )
        runs.append(run)
    return runs


@router.post("", response_model=BatchRunDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    files: list[UploadFile] = File(...),
    name: str | None = Form(default=None),
    profile_id: uuid.UUID | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_FILES} files allowed",
        )
    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one file required",
        )

    config_snapshot = None
    if profile_id is not None:
        from ocr_manga_title.db.crud import get_profile

        profile = await get_profile(db, profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )
        config_snapshot = build_run_config_snapshot(profile)

    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    batch = await create_batch_run(
        session=db, name=name, total_count=len(files)
    )

    runs = await _save_uploaded_files(files, batch.id, db, config_snapshot)

    await db.refresh(batch)
    return BatchRunDetailResponse(
        id=batch.id,
        name=batch.name,
        status=batch.status,
        total_count=batch.total_count,
        completed_count=batch.completed_count,
        failed_count=batch.failed_count,
        created_at=batch.created_at,
        completed_at=batch.completed_at,
        runs=[PipelineRunResponse.model_validate(r) for r in runs],
    )


@router.post("/{batch_id}/trigger", response_model=BatchRunResponse)
async def trigger_batch(
    batch_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(BatchRun)
        .where(BatchRun.id == batch_id)
        .options(selectinload(BatchRun.runs))
    )
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    if batch.status not in (BatchStatus.PENDING,):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Batch already {batch.status}")

    pending_runs = [r for r in batch.runs if r.status == RunStatus.PENDING]
    if not pending_runs:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No pending runs in batch")

    batch.status = BatchStatus.PROCESSING
    await db.commit()

    for run in pending_runs:
        process_pipeline_run.send(str(run.id))

    await db.refresh(batch)
    return BatchRunResponse.model_validate(batch)


@router.get("", response_model=PaginatedResponse[BatchRunResponse])
async def list_batches(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    batches = await list_batch_runs(db, status=status, limit=limit, offset=offset)
    total = await count_batch_runs(db, status=status)
    return PaginatedResponse(
        items=[BatchRunResponse.model_validate(b) for b in batches],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{batch_id}", response_model=BatchRunDetailResponse)
async def get_batch_detail(
    batch_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(BatchRun)
        .where(BatchRun.id == batch_id)
        .options(selectinload(BatchRun.runs))
    )
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    return BatchRunDetailResponse(
        id=batch.id,
        name=batch.name,
        status=batch.status,
        total_count=batch.total_count,
        completed_count=batch.completed_count,
        failed_count=batch.failed_count,
        created_at=batch.created_at,
        completed_at=batch.completed_at,
        runs=[PipelineRunResponse.model_validate(r) for r in batch.runs],
    )
