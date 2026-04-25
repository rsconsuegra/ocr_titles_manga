import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.pipeline import PipelineRunResponse
from ocr_manga_title.db.crud import create_pipeline_run, get_pipeline_run
from ocr_manga_title.services.config import build_run_config_snapshot
from ocr_manga_title.settings import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    MAX_FILES,
    UPLOAD_DIR,
)

router = APIRouter()

_UPLOAD_DIR = Path(UPLOAD_DIR)


async def _resolve_profile_snapshot(db: AsyncSession, profile_id: uuid.UUID | None):
    if profile_id is None:
        return None
    from ocr_manga_title.db.crud import get_profile

    profile = await get_profile(db, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    return build_run_config_snapshot(profile)


@router.post("/upload", response_model=list[PipelineRunResponse])
async def upload_images(
    files: list[UploadFile] = File(...),
    profile_id: uuid.UUID | None = Query(default=None),
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

    config_snapshot = await _resolve_profile_snapshot(db, profile_id)
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
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
            preprocess_config=config_snapshot,
        )
        runs.append(PipelineRunResponse.model_validate(run))

    return runs


@router.get("/{run_id}", response_model=PipelineRunResponse)
async def get_input(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve a pipeline run by ID."""
    run = await get_pipeline_run(session=db, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found"
        )
    return PipelineRunResponse.model_validate(run)
