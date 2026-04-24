# US-1B7: Configure Models via API

**Sub-phase**: 1B — FastAPI Application
**Depends on**: US-1A2 (seeded model_configs), US-1B1 (API structure)
**Blocks**: US-1C1 (worker reads model configs from DB)

---

## Overview

Create endpoints to list and update OCR model configurations. Operators use these to enable/disable models and adjust parameters without editing config files. The worker reads model configs from the database at runtime.

---

## Implementation Details

### 1. `ocr_manga_title/api/routes/models.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas import ModelConfigResponse, ModelConfigUpdateRequest
from ocr_manga_title.db.models import ModelConfig as ModelConfigDB
from ocr_manga_title.db.crud import get_model_config

router = APIRouter()

VALID_MODEL_NAMES = {"tesseract", "paddle", "easyocr", "glm_ocr"}

@router.get("", response_model=list[ModelConfigResponse])
async def list_models(db: AsyncSession = Depends(get_db)):
    stmt = select(ModelConfigDB).order_by(ModelConfigDB.model_name)
    result = await db.execute(stmt)
    return [ModelConfigResponse.model_validate(m) for m in result.scalars().all()]

@router.put("/{model_name}", response_model=ModelConfigResponse)
async def update_model(
    model_name: str,
    body: ModelConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    if model_name not in VALID_MODEL_NAMES:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

    from ocr_manga_title.db.crud import update_model_config
    updated = await update_model_config(
        session=db,
        model_name=model_name,
        **body.model_dump(exclude_none=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Model config not found: {model_name}")
    return ModelConfigResponse.model_validate(updated)
```

### 2. CRUD functions for model configs

```python
async def list_model_configs(session: AsyncSession) -> list[ModelConfig]:
    stmt = select(ModelConfig).order_by(ModelConfig.model_name)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def get_model_config(session: AsyncSession, model_name: str) -> ModelConfig | None:
    stmt = select(ModelConfig).where(ModelConfig.model_name == model_name)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def update_model_config(session: AsyncSession, model_name: str, **kwargs) -> ModelConfig | None:
    from datetime import datetime, timezone
    config = await get_model_config(session, model_name)
    if not config:
        return None
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    config.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(config)
    return config
```

---

## Acceptance Criteria

- [ ] `GET /api/v1/models` returns all 4 model configs
- [ ] Response includes: model_name, is_enabled, parameters, language_hint, updated_at
- [ ] `PUT /api/v1/models/tesseract` with `{"is_enabled": false}` disables tesseract
- [ ] `PUT /api/v1/models/paddle` with `{"is_enabled": true, "parameters": {"languages": ["en","ja"]}}` enables paddle with params
- [ ] Returns 404 for unknown model_name (e.g., "nonexistent_model")
- [ ] `updated_at` changes on every update
- [ ] Changes persist in database

---

## Test Specifications

**File**: `tests/test_api/test_models_route.py`

Tests:
- List models: returns 4 configs (tesseract enabled, 3 disabled)
- Get specific model fields: tesseract has is_enabled=True, parameters with psm/oem
- Update is_enabled to false: returns updated config
- Update parameters: returns updated config with new params
- Update language_hint: returns updated config
- Update nonexistent model: returns 404
- Verify updated_at changes after update
