from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.models import (
    ModelConfigResponse,
    ModelConfigUpdateRequest,
)
from ocr_manga_title.db.crud import update_model_config
from ocr_manga_title.db.models import ModelConfig as ModelConfigDB
from ocr_manga_title.engine.registry import MODEL_REGISTRY

router = APIRouter()


@router.get("", response_model=list[ModelConfigResponse])
async def list_models(db: AsyncSession = Depends(get_db)):
    """List all configured OCR model entries."""
    stmt = select(ModelConfigDB).order_by(ModelConfigDB.model_name)
    result = await db.execute(stmt)
    return [ModelConfigResponse.model_validate(m) for m in result.scalars().all()]


@router.put("/{model_name}", response_model=ModelConfigResponse)
async def update_model(
    model_name: str,
    body: ModelConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update configuration for a specific OCR model."""
    if model_name not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model not found: {model_name}",
        )

    updated = await update_model_config(
        session=db,
        model_name=model_name,
        **body.model_dump(exclude_none=True),
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model config not found: {model_name}",
        )
    return ModelConfigResponse.model_validate(updated)
