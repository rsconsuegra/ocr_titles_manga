# US-1A1: Store Pipeline Runs in Database

**Sub-phase**: 1A — Database Layer
**Depends on**: Step 1 (Project Setup — docker-compose.dev.yml, pyproject.toml deps, .env.example)
**Blocks**: US-1A2, US-1A3, US-1B1, US-1B2, US-1C1

---

## Overview

Create the async SQLAlchemy database session factory, all 6 ORM models, and the initial Alembic migration. This is the foundational ticket — every other V2 ticket depends on these tables existing.

---

## Implementation Details

### 1. `ocr_manga_title/db/__init__.py`

Empty init file. Export `Base` from models for convenience:

```python
from .models import Base
```

### 2. `ocr_manga_title/db/session.py`

Read `DATABASE_URL` from environment. Create async engine and session factory.

```python
import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://manga_ocr:manga_ocr_dev@localhost:5432/manga_ocr")

engine = create_async_engine(
    _database_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db_session():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

def get_engine():
    return engine
```

**Important**: If `DATABASE_URL` starts with `sqlite`, replace dialect with `aiosqlite` automatically (for tests). Add `connect_args={"check_same_thread": False}` for SQLite.

### 3. `ocr_manga_title/db/models.py`

6 SQLAlchemy 2.0 ORM models using `Mapped` type annotations:

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, Boolean, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    input_image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    preprocess_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    ocr_results: Mapped[list["OCRResult"]] = relationship(
        back_populates="pipeline_run", cascade="all, delete-orphan"
    )
    catalog_entries: Mapped[list["CatalogEntry"]] = relationship(
        back_populates="source_run"
    )

    __table_args__ = (
        Index("ix_pipeline_runs_status", "status"),
        Index("ix_pipeline_runs_created_at", "created_at"),
    )

class OCRResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    pipeline_run: Mapped["PipelineRun"] = relationship(back_populates="ocr_results")
    post_processing_results: Mapped[list["PostProcessingResult"]] = relationship(
        back_populates="ocr_result", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_ocr_results_pipeline_run_id", "pipeline_run_id"),
    )

class PostProcessingResult(Base):
    __tablename__ = "post_processing_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ocr_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ocr_results.id", ondelete="CASCADE"), nullable=False
    )
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompt_versions.id"), nullable=True
    )
    title_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title_ja: Mapped[str | None] = mapped_column(String(500), nullable=True)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    processing_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    ocr_result: Mapped["OCRResult"] = relationship(back_populates="post_processing_results")

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    agenta_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

class CatalogEntry(Base):
    __tablename__ = "catalog_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title_ja: Mapped[str | None] = mapped_column(String(500), nullable=True)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="needs_review")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    source_run: Mapped["PipelineRun"] = relationship(back_populates="catalog_entries")

    __table_args__ = (
        Index("ix_catalog_entries_code", "code"),
        Index("ix_catalog_entries_status", "status"),
    )

class ModelConfig(Base):
    __tablename__ = "model_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    language_hint: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

**Note on SQLite compat for tests**: When using aiosqlite, `JSONB` is not available. Use a type adapter or conditionally use `JSON` instead. The test conftest should handle this via a `TypeDecorator` or by overriding types.

### 4. `alembic.ini`

Standard Alembic config:
- `script_location = migrations`
- `sqlalchemy.url = ` (empty — set programmatically in env.py)

### 5. `migrations/env.py`

- Import `Base` from `ocr_manga_title.db.models`
- Read `DATABASE_URL` from env, set `sqlalchemy.url`
- Use `run_async` wrapper for async migrations
- `target_metadata = Base.metadata`

### 6. `migrations/script.py.mako`

Standard Alembic migration template with `Revision`, `Down_revision`, `upgrade()`, `downgrade()`.

### 7. `migrations/versions/001_initial.py`

Create all 6 tables:
- `pipeline_runs` with indexes on `status`, `created_at`
- `ocr_results` with index on `pipeline_run_id`, FK to `pipeline_runs`
- `post_processing_results` with FK to `ocr_results` and `prompt_versions`
- `prompt_versions`
- `catalog_entries` with indexes on `code`, `status`, FK to `pipeline_runs`
- `model_configs` with unique constraint on `model_name`

All UUID PKs use `postgresql.UUID(as_uuid=True)`. JSONB columns use `postgresql.JSONB`.

---

## Acceptance Criteria

- [ ] `ocr_manga_title/db/session.py` creates async engine from `DATABASE_URL` env var
- [ ] `ocr_manga_title/db/models.py` defines all 6 tables with correct columns, types, relationships, indexes
- [ ] `alembic.ini` and `migrations/env.py` configured for async migrations
- [ ] `migrations/versions/001_initial.py` creates all 6 tables
- [ ] `docker-compose -f docker-compose.dev.yml up -d` starts PostgreSQL
- [ ] `alembic upgrade head` creates all tables in PostgreSQL
- [ ] `alembic downgrade base` drops all tables cleanly
- [ ] In-memory SQLite session works for tests (aiosqlite compat)

---

## Test Specifications

**File**: `tests/test_db/conftest.py`

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from ocr_manga_title.db.models import Base

@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
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
```

**File**: `tests/test_db/test_models.py`

Tests:
- Create `PipelineRun` with all fields, verify UUID PK auto-generated
- Create `OCRResult` linked to pipeline_run, verify relationship loads
- Create `PostProcessingResult` linked to ocr_result, verify relationship
- Create `PromptVersion` with is_active flag
- Create `CatalogEntry` linked to pipeline_run
- Create `ModelConfig` with unique model_name
- Verify cascade: deleting PipelineRun cascades to OCRResult and PostProcessingResult
- Verify `created_at` defaults to now
- Verify `status` defaults: PipelineRun -> "pending", CatalogEntry -> "needs_review", ModelConfig is_enabled -> True
