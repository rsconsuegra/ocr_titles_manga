import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.pipeline import PaginatedResponse
from ocr_manga_title.api.schemas.results import (
    PostProcessingResultResponse,
    ResultOverrideRequest,
)
from ocr_manga_title.db.models import OCRResult, PostProcessingResult
from ocr_manga_title.services.pipeline import override_and_sync

router = APIRouter()


@router.get("", response_model=PaginatedResponse[PostProcessingResultResponse])
async def list_results(
    model_name: str | None = None,
    min_confidence: float | None = None,
    max_confidence: float | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List post-processing results with optional filtering and pagination."""
    stmt = (
        select(PostProcessingResult)
        .join(OCRResult)
        .order_by(PostProcessingResult.created_at.desc())
    )
    count_stmt = (
        select(sa_func.count()).select_from(PostProcessingResult).join(OCRResult)
    )

    if model_name:
        stmt = stmt.where(OCRResult.model_name == model_name)
        count_stmt = count_stmt.where(OCRResult.model_name == model_name)
    if min_confidence is not None:
        stmt = stmt.where(PostProcessingResult.confidence >= min_confidence)
        count_stmt = count_stmt.where(PostProcessingResult.confidence >= min_confidence)
    if max_confidence is not None:
        stmt = stmt.where(PostProcessingResult.confidence <= max_confidence)
        count_stmt = count_stmt.where(PostProcessingResult.confidence <= max_confidence)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = [
        PostProcessingResultResponse.model_validate(r) for r in result.scalars().all()
    ]

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.put("/{result_id}/override", response_model=PostProcessingResultResponse)
async def override_result(
    result_id: uuid.UUID,
    body: ResultOverrideRequest,
    db: AsyncSession = Depends(get_db),
):
    """Override title fields on a post-processing result and sync the catalog entry."""
    pp_result = await override_and_sync(
        db,
        result_id,
        body.model_dump(exclude_none=True),
    )
    if not pp_result:
        raise HTTPException(status_code=404, detail="Post-processing result not found")
    return PostProcessingResultResponse.model_validate(pp_result)
