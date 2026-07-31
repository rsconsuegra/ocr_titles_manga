"""Async CRUD helpers for all database models."""

import uuid
from typing import Any

from sqlalchemy import func as sa_func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, selectinload

from ocr_manga_title.db.enums import BatchStatus, RunStatus
from ocr_manga_title.db.models import (
    BatchRun,
    CatalogEntry,
    ModelConfig,
    OCRResult,
    PipelineProfile,
    PipelineRun,
    PromptVersion,
)
from ocr_manga_title.schemas import utcnow

_VALID_MODEL_CONFIG_COLS = {
    "is_enabled",
    "parameters",
    "language_hint",
}
_VALID_CATALOG_ENTRY_COLS = {
    "status",
    "title_en",
    "title_ja",
    "code",
    "updated_at",
}
_VALID_BATCH_RUN_COLS = {
    "status",
    "completed_count",
    "failed_count",
    "completed_at",
}
_VALID_PIPELINE_RUN_COLS = {
    "input_image_path",
    "source_url",
    "source_platform",
    "status",
    "error_message",
    "preprocess_config",
    "batch_run_id",
    "completed_at",
}
_VALID_PROFILE_COLS = {
    "name",
    "description",
    "preprocess_steps",
    "ocr_models",
    "enable_llm",
    "llm_provider",
    "llm_config",
    "is_default",
}


async def _get_by(
    session: AsyncSession,
    model_cls: type,
    column: InstrumentedAttribute[Any],
    value: Any,
) -> Any | None:
    stmt: Any = select(model_cls).where(column == value)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _list_paginated(
    session: AsyncSession,
    model_cls: type,
    order_col: Any,
    limit: int,
    offset: int,
    filter_col: InstrumentedAttribute[Any] | None = None,
    filter_val: Any = None,
) -> list[Any]:
    stmt: Any = select(model_cls).order_by(order_col).offset(offset).limit(limit)
    if filter_col is not None and filter_val is not None:
        stmt = stmt.where(filter_col == filter_val)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _count_rows(
    session: AsyncSession,
    model_cls: type,
    filter_col: InstrumentedAttribute[Any] | None = None,
    filter_val: Any = None,
) -> int:
    stmt: Any = select(sa_func.count()).select_from(model_cls)
    if filter_col is not None and filter_val is not None:
        stmt = stmt.where(filter_col == filter_val)
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def _apply_updates(
    entity: Any,
    valid_cols: set[str],
    kwargs: dict[str, Any],
    session: AsyncSession,
) -> None:
    unknown = set(kwargs) - valid_cols
    if unknown:
        raise TypeError(f"Unknown {type(entity).__name__} fields: {unknown}")
    for key, value in kwargs.items():
        setattr(entity, key, value)
    await session.flush()
    await session.refresh(entity)


async def get_active_prompt(
    session: AsyncSession, prompt_type: str
) -> PromptVersion | None:
    """Return the currently active prompt for the given type, or None."""
    stmt = (
        select(PromptVersion)
        .where(
            PromptVersion.prompt_type == prompt_type, PromptVersion.is_active.is_(True)
        )
        .order_by(PromptVersion.version_number.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_prompts(
    session: AsyncSession, prompt_type: str | None = None
) -> list[PromptVersion]:
    """Return all prompt versions, optionally filtered by type."""
    stmt = select(PromptVersion).order_by(PromptVersion.created_at.desc())
    if prompt_type:
        stmt = stmt.where(PromptVersion.prompt_type == prompt_type)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_model_config(
    session: AsyncSession, model_name: str
) -> ModelConfig | None:
    """Look up a model configuration by name."""
    return await _get_by(session, ModelConfig, ModelConfig.model_name, model_name)


async def list_model_configs(
    session: AsyncSession, enabled_only: bool = False
) -> list[ModelConfig]:
    """Return all model configs, optionally filtered to enabled only."""
    if enabled_only:
        stmt = (
            select(ModelConfig)
            .where(ModelConfig.is_enabled.is_(True))
            .order_by(ModelConfig.model_name)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    return await _list_paginated(
        session, ModelConfig, ModelConfig.model_name, limit=10000, offset=0
    )


async def update_model_config(
    session: AsyncSession, model_name: str, **kwargs: Any
) -> ModelConfig | None:
    """Update fields on an existing model configuration."""
    config = await get_model_config(session, model_name)
    if config is None:
        return None
    await _apply_updates(config, _VALID_MODEL_CONFIG_COLS, kwargs, session)
    return config


async def create_pipeline_run(session: AsyncSession, **kwargs: Any) -> PipelineRun:
    """Insert a new pipeline run record."""
    unknown = set(kwargs) - _VALID_PIPELINE_RUN_COLS
    if unknown:
        raise TypeError(f"Unknown PipelineRun fields: {unknown}")
    run = PipelineRun(**kwargs)
    session.add(run)
    await session.flush()
    await session.refresh(run)
    return run


async def get_pipeline_run(
    session: AsyncSession, run_id: uuid.UUID
) -> PipelineRun | None:
    """Fetch a single pipeline run by its ID."""
    return await _get_by(session, PipelineRun, PipelineRun.id, run_id)


async def list_pipeline_runs(
    session: AsyncSession, status: str | None = None, limit: int = 20, offset: int = 0
) -> list[PipelineRun]:
    """Return pipeline runs with optional status filter and pagination."""
    return await _list_paginated(
        session,
        PipelineRun,
        PipelineRun.created_at.desc(),
        limit,
        offset,
        PipelineRun.status,
        status,
    )


async def count_pipeline_runs(session: AsyncSession, status: str | None = None) -> int:
    """Count pipeline runs, optionally filtered by status."""
    return await _count_rows(session, PipelineRun, PipelineRun.status, status)


async def get_pipeline_run_detail(
    session: AsyncSession, run_id: uuid.UUID
) -> PipelineRun | None:
    """Fetch a pipeline run with eager-loaded OCR and post-processing results."""
    stmt = (
        select(PipelineRun)
        .where(PipelineRun.id == run_id)
        .options(
            selectinload(PipelineRun.ocr_results).selectinload(
                OCRResult.post_processing_results
            )
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_catalog_entry(
    session: AsyncSession, entry_id: uuid.UUID
) -> CatalogEntry | None:
    """Fetch a single catalog entry by its ID."""
    return await _get_by(session, CatalogEntry, CatalogEntry.id, entry_id)


async def list_catalog_entries(
    session: AsyncSession, status: str | None = None, limit: int = 50, offset: int = 0
) -> list[CatalogEntry]:
    """Return catalog entries with optional status filter and pagination."""
    return await _list_paginated(
        session,
        CatalogEntry,
        CatalogEntry.created_at.desc(),
        limit,
        offset,
        CatalogEntry.status,
        status,
    )


async def count_catalog_entries(
    session: AsyncSession, status: str | None = None
) -> int:
    """Count catalog entries, optionally filtered by status."""
    return await _count_rows(session, CatalogEntry, CatalogEntry.status, status)


async def update_catalog_entry(
    session: AsyncSession, entry_id: uuid.UUID, **kwargs: Any
) -> CatalogEntry | None:
    """Update fields on an existing catalog entry."""
    entry = await get_catalog_entry(session, entry_id)
    if not entry:
        return None
    await _apply_updates(entry, _VALID_CATALOG_ENTRY_COLS, kwargs, session)
    return entry


async def get_catalog_entry_by_run(
    session: AsyncSession, run_id: uuid.UUID
) -> CatalogEntry | None:
    """Find the catalog entry associated with a pipeline run."""
    return await _get_by(session, CatalogEntry, CatalogEntry.source_run_id, run_id)


async def create_batch_run(
    session: AsyncSession, *, name: str | None, total_count: int, **kwargs: Any
) -> BatchRun:
    """Insert a new batch run record."""
    unknown = set(kwargs) - _VALID_BATCH_RUN_COLS
    if unknown:
        raise TypeError(f"Unknown BatchRun fields: {unknown}")
    batch = BatchRun(name=name, total_count=total_count, **kwargs)
    session.add(batch)
    await session.flush()
    await session.refresh(batch)
    return batch


async def get_batch_run(session: AsyncSession, batch_id: uuid.UUID) -> BatchRun | None:
    """Fetch a single batch run by its ID."""
    return await _get_by(session, BatchRun, BatchRun.id, batch_id)


async def list_batch_runs(
    session: AsyncSession,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[BatchRun]:
    """Return batch runs with optional status filter and pagination."""
    return await _list_paginated(
        session,
        BatchRun,
        BatchRun.created_at.desc(),
        limit,
        offset,
        BatchRun.status,
        status,
    )


async def count_batch_runs(session: AsyncSession, status: str | None = None) -> int:
    """Count batch runs, optionally filtered by status."""
    return await _count_rows(session, BatchRun, BatchRun.status, status)


async def update_batch_run(
    session: AsyncSession, batch_id: uuid.UUID, **kwargs: Any
) -> BatchRun | None:
    """Update fields on an existing batch run."""
    batch = await get_batch_run(session, batch_id)
    if not batch:
        return None
    await _apply_updates(batch, _VALID_BATCH_RUN_COLS, kwargs, session)
    return batch


async def update_batch_progress(
    session: AsyncSession, batch_id: uuid.UUID
) -> BatchRun | None:
    """Recalculate counters and status for a batch run after a child run finishes."""
    batch = await get_batch_run(session, batch_id)
    if not batch:
        return None

    completed = (
        await session.execute(
            select(sa_func.count())
            .select_from(PipelineRun)
            .where(
                PipelineRun.batch_run_id == batch_id,
                PipelineRun.status == RunStatus.COMPLETED,
            )
        )
    ).scalar_one()

    failed = (
        await session.execute(
            select(sa_func.count())
            .select_from(PipelineRun)
            .where(
                PipelineRun.batch_run_id == batch_id,
                PipelineRun.status == RunStatus.FAILED,
            )
        )
    ).scalar_one()

    batch.completed_count = completed
    batch.failed_count = failed

    finished = completed + failed
    if finished >= batch.total_count:
        if failed == 0:
            batch.status = BatchStatus.COMPLETED
        else:
            batch.status = BatchStatus.PARTIAL_FAILURE
        batch.completed_at = utcnow()

    await session.flush()
    await session.refresh(batch)
    return batch


async def _unset_default_profiles(session: AsyncSession) -> None:
    stmt = (
        update(PipelineProfile)
        .where(PipelineProfile.is_default.is_(True))
        .values(is_default=False)
    )
    await session.execute(stmt)


async def create_profile(
    session: AsyncSession,
    *,
    name: str,
    description: str | None = None,
    preprocess_steps: dict[str, Any] | None = None,
    ocr_models: dict[str, Any] | None = None,
    enable_llm: bool = False,
    llm_provider: str = "openrouter",
    llm_config: dict[str, Any] | None = None,
    is_default: bool = False,
) -> PipelineProfile:
    """Create a new pipeline profile in the database."""
    if is_default:
        await _unset_default_profiles(session)
    profile = PipelineProfile(
        name=name,
        description=description,
        preprocess_steps=preprocess_steps,
        ocr_models=ocr_models,
        enable_llm=enable_llm,
        llm_provider=llm_provider,
        llm_config=llm_config,
        is_default=is_default,
    )
    session.add(profile)
    await session.flush()
    await session.refresh(profile)
    return profile


async def get_profile(
    session: AsyncSession, profile_id: uuid.UUID
) -> PipelineProfile | None:
    """Retrieve a profile by its primary key."""
    return await _get_by(session, PipelineProfile, PipelineProfile.id, profile_id)


async def get_profile_by_name(
    session: AsyncSession, name: str
) -> PipelineProfile | None:
    """Retrieve a profile by its unique name."""
    return await _get_by(session, PipelineProfile, PipelineProfile.name, name)


async def get_default_profile(session: AsyncSession) -> PipelineProfile | None:
    """Retrieve the currently marked default profile, if any."""
    stmt = select(PipelineProfile).where(PipelineProfile.is_default.is_(True))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_profiles(
    session: AsyncSession, limit: int = 50, offset: int = 0
) -> list[PipelineProfile]:
    """Return a paginated list of profiles ordered by name."""
    return await _list_paginated(
        session, PipelineProfile, PipelineProfile.name, limit, offset
    )


async def count_profiles(session: AsyncSession) -> int:
    """Return the total number of profiles."""
    return await _count_rows(session, PipelineProfile)


async def update_profile(
    session: AsyncSession, profile_id: uuid.UUID, **kwargs: Any
) -> PipelineProfile | None:
    """Update selected fields on an existing profile."""
    profile = await get_profile(session, profile_id)
    if not profile:
        return None
    if kwargs.get("is_default") is True:
        await _unset_default_profiles(session)
    await _apply_updates(profile, _VALID_PROFILE_COLS, kwargs, session)
    return profile


async def delete_profile(session: AsyncSession, profile_id: uuid.UUID) -> bool:
    """Delete a profile by its primary key."""
    profile = await get_profile(session, profile_id)
    if not profile:
        return False
    await session.delete(profile)
    await session.flush()
    return True
