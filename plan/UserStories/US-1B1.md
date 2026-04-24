# US-1B1: Upload Images via API

**Sub-phase**: 1B — FastAPI Application
**Depends on**: US-1A1 (PipelineRun table), Step 1 (Project Setup — FastAPI dep)
**Blocks**: US-1B2 (trigger needs uploaded images), US-1D1 (frontend upload)

---

## Overview

Create the FastAPI application factory, dependency injection layer, API schemas, and the input upload endpoint. This is the first API endpoint and establishes the FastAPI app structure that all other routes build on.

---

## Implementation Details

### 1. `ocr_manga_title/api/__init__.py`

Empty init.

### 2. `ocr_manga_title/api/app.py`

FastAPI app factory:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ocr_manga_title.api.routes import inputs, pipeline, results, catalog, models as models_route

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

def create_app() -> FastAPI:
    app = FastAPI(
        title="Manga OCR API",
        version="0.2.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(inputs.router, prefix="/api/v1/inputs", tags=["inputs"])
    app.include_router(pipeline.router, prefix="/api/v1/pipeline", tags=["pipeline"])
    app.include_router(results.router, prefix="/api/v1/results", tags=["results"])
    app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["catalog"])
    app.include_router(models_route.router, prefix="/api/v1/models", tags=["models"])
    return app
```

### 3. `ocr_manga_title/api/dependencies.py`

```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from ocr_manga_title.db.session import async_session_factory
from ocr_manga_title.config import load_config, load_ocr_config, load_preprocess_config
from ocr_manga_title.schemas import AppConfig

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

def get_config() -> AppConfig:
    return load_config("configs.toml")
```

### 4. `ocr_manga_title/api/schemas.py`

Request/response Pydantic models:

```python
import uuid
from datetime import datetime
from pydantic import BaseModel

class PipelineRunResponse(BaseModel):
    id: uuid.UUID
    input_image_path: str
    status: str
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}

class OCRResultResponse(BaseModel):
    id: uuid.UUID
    model_name: str
    raw_text: str
    confidence: float
    processing_time_ms: int
    error: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

class PostProcessingResultResponse(BaseModel):
    id: uuid.UUID
    title_en: str | None = None
    title_ja: str | None = None
    code: str | None = None
    confidence: float
    processing_type: str
    created_at: datetime

    model_config = {"from_attributes": True}

class CatalogEntryResponse(BaseModel):
    id: uuid.UUID
    title_en: str | None = None
    title_ja: str | None = None
    code: str | None = None
    source_run_id: uuid.UUID
    confidence: float
    status: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}

class ModelConfigResponse(BaseModel):
    model_name: str
    is_enabled: bool
    parameters: dict | None = None
    language_hint: str | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}

class PaginatedResponse(BaseModel):
    items: list
    total: int
    limit: int
    offset: int

class ResultOverrideRequest(BaseModel):
    title_en: str | None = None
    title_ja: str | None = None
    code: str | None = None

class CatalogUpdateRequest(BaseModel):
    status: str | None = None
    title_en: str | None = None
    title_ja: str | None = None
    code: str | None = None

class ModelConfigUpdateRequest(BaseModel):
    is_enabled: bool | None = None
    parameters: dict | None = None
    language_hint: str | None = None

class PipelineTriggerRequest(BaseModel):
    preprocess_enabled: bool = True
```

### 5. `ocr_manga_title/api/routes/__init__.py`

Empty init.

### 6. `ocr_manga_title/api/routes/inputs.py`

```python
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas import PipelineRunResponse
from ocr_manga_title.db.crud import create_pipeline_run

router = APIRouter()

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_FILES = 10
UPLOAD_DIR = Path("uploads")

@router.post("/upload", response_model=list[PipelineRunResponse])
async def upload_images(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} files allowed")
    if len(files) == 0:
        raise HTTPException(status_code=422, detail="At least one file required")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    runs = []

    for file in files:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Invalid format: {ext}. Allowed: {ALLOWED_EXTENSIONS}")

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"File too large: {file.filename} (max 20MB)")

        file_id = uuid.uuid4()
        save_path = UPLOAD_DIR / f"{file_id}{ext}"
        save_path.write_bytes(content)

        run = await create_pipeline_run(
            session=db,
            input_image_path=str(save_path),
            source_platform="manual",
        )
        runs.append(PipelineRunResponse.model_validate(run))

    return runs

@router.get("/{run_id}", response_model=PipelineRunResponse)
async def get_input(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    run = await get_pipeline_run(session=db, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return PipelineRunResponse.model_validate(run)
```

### 7. `ocr_manga_title/db/crud.py` (pipeline run functions)

```python
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from ocr_manga_title.db.models import PipelineRun
import uuid

async def create_pipeline_run(
    session: AsyncSession,
    input_image_path: str,
    source_url: str | None = None,
    source_platform: str | None = "manual",
    preprocess_config: dict | None = None,
) -> PipelineRun:
    run = PipelineRun(
        input_image_path=input_image_path,
        source_url=source_url,
        source_platform=source_platform,
        preprocess_config=preprocess_config,
    )
    session.add(run)
    await session.flush()
    await session.refresh(run)
    return run

async def get_pipeline_run(session: AsyncSession, run_id: uuid.UUID) -> PipelineRun | None:
    stmt = select(PipelineRun).where(PipelineRun.id == run_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def list_pipeline_runs(
    session: AsyncSession,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[PipelineRun]:
    stmt = select(PipelineRun).order_by(PipelineRun.created_at.desc()).offset(offset).limit(limit)
    if status:
        stmt = stmt.where(PipelineRun.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def update_pipeline_run_status(
    session: AsyncSession,
    run_id: uuid.UUID,
    status: str,
    error_message: str | None = None,
) -> PipelineRun | None:
    from datetime import datetime, timezone
    run = await get_pipeline_run(session, run_id)
    if not run:
        return None
    run.status = status
    run.error_message = error_message
    if status in ("completed", "failed"):
        run.completed_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(run)
    return run
```

---

## Acceptance Criteria

- [ ] `POST /api/v1/inputs/upload` accepts multipart form with 1-10 images
- [ ] Files saved to `uploads/` directory with UUID filenames
- [ ] Each file creates a `pipeline_runs` row with status="pending"
- [ ] Returns list of `PipelineRunResponse` with IDs
- [ ] Returns 400 for invalid file format (e.g., `.gif`, `.pdf`)
- [ ] Returns 400 for files > 20MB
- [ ] Returns 400 for > 10 files
- [ ] Returns 422 for zero files
- [ ] `GET /api/v1/inputs/{run_id}` returns run status
- [ ] Returns 404 for nonexistent run_id
- [ ] OpenAPI docs available at `/api/docs`

---

## Test Specifications

**File**: `tests/test_api/conftest.py`

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from ocr_manga_title.db.models import Base
from ocr_manga_title.api.app import create_app

@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

@pytest.fixture
async def client(db_engine, monkeypatch):
    from ocr_manga_title.db import session as session_module
    test_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(session_module, "async_session_factory", test_factory)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

**File**: `tests/test_api/test_inputs.py`

Tests:
- Upload 1 valid PNG (blank_image fixture): returns 200 with 1 PipelineRunResponse, status="pending"
- Upload 3 valid images: returns 200 with 3 PipelineRunResponses
- Upload 0 files: returns 422
- Upload 11 files: returns 400
- Upload file with .gif extension: returns 400
- Upload file > 20MB: returns 400 (create large file fixture)
- `GET /api/v1/inputs/{run_id}` after upload: returns correct PipelineRunResponse
- `GET /api/v1/inputs/{random_uuid}`: returns 404
