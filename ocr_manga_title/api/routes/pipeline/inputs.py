"""Image upload and pipeline run creation endpoints."""

import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.routes._helpers import (
    get_pipeline_run_or_404,
    resolve_profile_snapshot,
    validate_and_save_file,
    validate_file_count,
)
from ocr_manga_title.api.schemas.pipeline import PipelineRunResponse
from ocr_manga_title.db.crud import create_pipeline_run

router = APIRouter()


@router.post("/upload", response_model=list[PipelineRunResponse])
async def upload_images(
    files: list[UploadFile] = File(...),
    profile_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[PipelineRunResponse]:
    """Upload images and create individual pipeline runs."""
    validate_file_count(files)

    config_snapshot = await resolve_profile_snapshot(db, profile_id)
    runs = []

    for file in files:
        save_path = await validate_and_save_file(file)

        run = await create_pipeline_run(
            session=db,
            input_image_path=str(save_path),
            source_platform="manual",
            preprocess_config=config_snapshot,
        )
        runs.append(PipelineRunResponse.model_validate(run))

    return runs


@router.get("/{run_id}", response_model=PipelineRunResponse)
async def get_input(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> PipelineRunResponse:
    """Retrieve a single pipeline run by ID."""
    run = await get_pipeline_run_or_404(db, run_id)
    return PipelineRunResponse.model_validate(run)
