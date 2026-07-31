"""OCR model configuration endpoints - list and upsert per-model settings."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.models import (
    ModelConfigResponse,
    ModelConfigUpdateRequest,
)
from ocr_manga_title.config import resolve_model_configs
from ocr_manga_title.db.crud import get_model_config
from ocr_manga_title.db.models import ModelConfig as ModelConfigDB
from ocr_manga_title.engine.registry import MODEL_REGISTRY

router = APIRouter()


def _db_row_to_dict(row: ModelConfigDB) -> dict[str, Any]:
    return {"is_enabled": row.is_enabled, "parameters": row.parameters or {}}


@router.get("", response_model=list[ModelConfigResponse])
async def list_models(db: AsyncSession = Depends(get_db)) -> list[ModelConfigResponse]:
    """List all OCR model configs — merged from YAML defaults and DB overrides."""
    stmt = select(ModelConfigDB)
    result = await db.execute(stmt)
    db_overrides = {m.model_name: _db_row_to_dict(m) for m in result.scalars().all()}

    resolved = resolve_model_configs(db_overrides)

    response = []
    for name in MODEL_REGISTRY:
        cfg = resolved.get(name)
        db_row = await get_model_config(db, name)
        response.append(
            ModelConfigResponse(
                model_name=name,
                is_enabled=cfg.enabled if cfg else True,
                parameters=cfg.parameters if cfg else {},
                language_hint=db_row.language_hint if db_row else None,
                updated_at=db_row.updated_at if db_row else None,
            )
        )
    return response


@router.put("/{model_name}", response_model=ModelConfigResponse)
async def update_model(
    model_name: str,
    body: ModelConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ModelConfigResponse:
    """Upsert configuration for a specific OCR model."""
    if model_name not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model not found: {model_name}",
        )

    import uuid

    existing = await get_model_config(db, model_name)
    if existing is None:
        existing = ModelConfigDB(
            id=uuid.uuid4(),
            model_name=model_name,
            is_enabled=True,
            parameters={},
        )
        db.add(existing)
        await db.flush()

    updates = body.model_dump(exclude_none=True)
    for key, value in updates.items():
        setattr(existing, key, value)
    await db.flush()
    await db.refresh(existing)
    return ModelConfigResponse.model_validate(existing)
