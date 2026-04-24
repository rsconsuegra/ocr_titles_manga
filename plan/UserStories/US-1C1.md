# US-1C1: Process OCR Jobs Asynchronously

**Sub-phase**: 1C — Task Queue
**Depends on**: US-1A1 (DB tables), US-1A2 (seeded models), US-1A3 (seeded prompt), US-1B2 (trigger endpoint), US-1B7 (model configs in DB)
**Blocks**: US-1C2 (retry builds on this worker)

---

## Overview

Implement the Dramatiq worker actor that processes pipeline runs end-to-end: loads config from database, runs `OCREngine.process()`, stores all results in database. This is the core async processing bridge between the API and the OCR engine.

---

## Implementation Details

### Key Design Constraint

`OCREngine.process()` is **synchronous** (uses `ThreadPoolExecutor` internally). Dramatiq actors are also synchronous. The **database operations** are async. The worker must bridge sync/async:

```python
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
```

### 1. `ocr_manga_title/workers/ocr_worker.py`

```python
import logging
import uuid
import asyncio
from pathlib import Path

import dramatiq
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.workers.broker import broker  # noqa: F401
from ocr_manga_title.db.session import async_session_factory
from ocr_manga_title.db.models import (
    PipelineRun, OCRResult as OCRResultDB,
    PostProcessingResult, CatalogEntry, ModelConfig, PromptVersion
)
from ocr_manga_title.config import load_config
from ocr_manga_title.schemas import ModelConfig as ModelConfigSchema
from ocr_manga_title.engine import OCREngine

logger = logging.getLogger(__name__)

def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def _get_model_configs(session: AsyncSession) -> dict[str, ModelConfigSchema]:
    stmt = select(ModelConfig).where(ModelConfig.is_enabled == True)
    result = await session.execute(stmt)
    configs = {}
    for row in result.scalars().all():
        configs[row.model_name] = ModelConfigSchema(
            name=row.model_name,
            enabled=row.is_enabled,
            language=row.language_hint or "",
            parameters=row.parameters or {},
        )
    return configs

async def _get_active_prompt_content(session: AsyncSession) -> str | None:
    stmt = select(PromptVersion).where(
        PromptVersion.prompt_type == "llm",
        PromptVersion.is_active == True,
    ).limit(1)
    result = await session.execute(stmt)
    prompt = result.scalar_one_or_none()
    if prompt:
        return prompt.content
    return None

@dramatiq.actor(
    max_retries=3,
    min_backoff=10000,
    max_backoff=60000,
    time_limit=300000,
)
def process_pipeline_run(run_id: str):
    _run_async(_process(run_id))

async def _process(run_id: str):
    async with async_session_factory() as session:
        try:
            run_uuid = uuid.UUID(run_id)
        except ValueError:
            logger.error(f"Invalid run_id: {run_id}")
            return

        # Fetch run
        stmt = select(PipelineRun).where(PipelineRun.id == run_uuid)
        result = await session.execute(stmt)
        run = result.scalar_one_or_none()
        if not run:
            logger.error(f"Pipeline run not found: {run_id}")
            return

        # Update status to processing
        run.status = "processing"
        await session.commit()

        try:
            # Load config
            app_config = load_config("configs.toml")
            model_configs = await _get_model_configs(session)

            # Load prompt (DB > file fallback)
            prompt_content = await _get_active_prompt_content(session)
            prompt_path = None
            if not prompt_content:
                prompt_path = Path("prompts/llm/extract_title_v1.md")

            # Load preprocess config
            from ocr_manga_title.config import load_preprocess_config
            preprocess_config = load_preprocess_config("preprocess.yaml")

            # Create engine and run
            engine = OCREngine(
                config=app_config,
                ocr_config=model_configs,
                preprocess_config=preprocess_config,
            )

            pipeline_result = engine.process(run.input_image_path)

            # Store OCR results
            for ocr_result in pipeline_result.ocr_results:
                ocr_db = OCRResultDB(
                    pipeline_run_id=run.id,
                    model_name=ocr_result.model_name,
                    raw_text=ocr_result.raw_text,
                    confidence=ocr_result.confidence,
                    processing_time_ms=ocr_result.processing_time_ms,
                    error=ocr_result.error,
                )
                session.add(ocr_db)
                await session.flush()

            # Store post-processing results from PipelineResult.extracted
            if pipeline_result.extracted:
                # Find the OCRResult that produced the best extraction
                best_ocr = None
                for ocr_result in pipeline_result.ocr_results:
                    if ocr_result.model_name == pipeline_result.extracted.source_model:
                        best_ocr = ocr_result
                        break

                if best_ocr:
                    # Get the DB OCRResult we just stored
                    stmt2 = select(OCRResultDB).where(
                        OCRResultDB.pipeline_run_id == run.id,
                        OCRResultDB.model_name == best_ocr.model_name,
                    )
                    r2 = await session.execute(stmt2)
                    ocr_db = r2.scalars().first()

                    if ocr_db:
                        pp_result = PostProcessingResult(
                            ocr_result_id=ocr_db.id,
                            title_en=pipeline_result.extracted.title_en,
                            title_ja=pipeline_result.extracted.title_ja,
                            code=pipeline_result.extracted.code,
                            confidence=pipeline_result.extracted.confidence,
                            processing_type=pipeline_result.extracted.source_method or "unknown",
                        )
                        session.add(pp_result)

                # Create catalog entry
                if pipeline_result.extracted.confidence > 0.0:
                    catalog_entry = CatalogEntry(
                        source_run_id=run.id,
                        title_en=pipeline_result.extracted.title_en,
                        title_ja=pipeline_result.extracted.title_ja,
                        code=pipeline_result.extracted.code,
                        confidence=pipeline_result.extracted.confidence,
                    )
                    session.add(catalog_entry)

            # Mark completed
            from datetime import datetime, timezone
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()

            logger.info(f"Pipeline run {run_id} completed successfully")

        except Exception as e:
            from datetime import datetime, timezone
            run.status = "failed"
            run.error_message = str(e)[:1000]
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()
            logger.error(f"Pipeline run {run_id} failed: {e}")
            raise
```

### 2. Worker process entry point

The worker runs as a separate process:
```bash
dramatiq ocr_manga_title.workers.ocr_worker
```

This is added to the Makefile as `make worker`.

---

## Acceptance Criteria

- [ ] `process_pipeline_run.send(run_id)` enqueues a job
- [ ] Worker fetches run from database, updates status to "processing"
- [ ] Worker creates `OCREngine` with DB model configs (enabled models from `model_configs` table)
- [ ] Worker loads active prompt from `prompt_versions` table (falls back to file)
- [ ] `OCREngine.process()` runs and returns `PipelineResult`
- [ ] Each `OCRResult` stored in `ocr_results` table
- [ ] `ExtractedTitle` stored in `post_processing_results` table
- [ ] Catalog entry created when confidence > 0.0
- [ ] Run status updated to "completed" with `completed_at` timestamp
- [ ] On error: status set to "failed" with `error_message`, exception re-raised for retry
- [ ] Worker logs progress at INFO level

---

## Test Specifications

**File**: `tests/test_worker/conftest.py`

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from ocr_manga_title.db.models import Base

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
```

**File**: `tests/test_worker/test_ocr_worker.py`

Tests (all with mocked OCREngine):
- Successful pipeline run: run transitions pending -> processing -> completed
- OCR results stored: verify correct model_name, raw_text, confidence, processing_time_ms
- Post-processing result stored: verify title_en, title_ja, code, confidence, processing_type
- Catalog entry created when extraction confidence > 0.0
- No catalog entry created when extraction confidence == 0.0
- Failed pipeline (engine raises): run status = "failed", error_message populated
- Missing run_id: worker logs error, does not crash
- Invalid run_id format: worker logs error, does not crash
- Model config loaded from DB: only enabled models passed to OCREngine

**Mocking strategy**: Patch `OCREngine.process` to return a fake `PipelineResult`. Patch `load_config` to return fake `AppConfig`. Verify DB state after each scenario.
