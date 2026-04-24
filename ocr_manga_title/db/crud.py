import uuid
from datetime import UTC, datetime

from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ocr_manga_title.db.models import (
    BatchRun,
    CatalogEntry,
    ModelConfig,
    OCRResult,
    PipelineProfile,
    PipelineRun,
    PromptVersion,
)


async def get_active_prompt(
    session: AsyncSession, prompt_type: str
) -> PromptVersion | None:
    """Return the currently active prompt for the given type, or None.

    Args:
        session: Async database session.
        prompt_type: Category of prompt (e.g. "llm").

    Returns:
        The active :class:`PromptVersion` or ``None`` if no active version exists.

    """
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
    """Return all prompt versions, optionally filtered by type.

    Args:
        session: Async database session.
        prompt_type: Optional type filter.

    Returns:
        List of :class:`PromptVersion` rows ordered newest-first.

    """
    stmt = select(PromptVersion).order_by(PromptVersion.created_at.desc())
    if prompt_type:
        stmt = stmt.where(PromptVersion.prompt_type == prompt_type)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_model_config(
    session: AsyncSession, model_name: str
) -> ModelConfig | None:
    """Look up a model configuration by name.

    Args:
        session: Async database session.
        model_name: Unique model identifier.

    Returns:
        The matching :class:`ModelConfig` or ``None``.

    """
    stmt = select(ModelConfig).where(ModelConfig.model_name == model_name)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_model_configs(
    session: AsyncSession, enabled_only: bool = False
) -> list[ModelConfig]:
    """Return all model configs, optionally filtered to enabled only.

    Args:
        session: Async database session.
        enabled_only: When ``True``, exclude disabled models.

    Returns:
        List of :class:`ModelConfig` rows ordered by name.

    """
    stmt = select(ModelConfig).order_by(ModelConfig.model_name)
    if enabled_only:
        stmt = stmt.where(ModelConfig.is_enabled.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_model_config(
    session: AsyncSession, model_name: str, **kwargs
) -> ModelConfig | None:
    """Update fields on an existing model configuration.

    Args:
        session: Async database session.
        model_name: Unique model identifier.
        **kwargs: Fields to update.

    Returns:
        The updated :class:`ModelConfig` or ``None`` if not found.

    """
    config = await get_model_config(session, model_name)
    if config is None:
        return None
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    await session.flush()
    await session.refresh(config)
    return config


async def create_pipeline_run(session: AsyncSession, **kwargs) -> PipelineRun:
    """Insert a new pipeline run record.

    Args:
        session: Async database session.
        **kwargs: Column values for the new row.

    Returns:
        The freshly created :class:`PipelineRun`.

    """
    run = PipelineRun(**kwargs)
    session.add(run)
    await session.flush()
    await session.refresh(run)
    return run


async def get_pipeline_run(session: AsyncSession, run_id) -> PipelineRun | None:
    """Fetch a single pipeline run by its ID.

    Args:
        session: Async database session.
        run_id: UUID of the pipeline run.

    Returns:
        The matching :class:`PipelineRun` or ``None``.

    """
    stmt = select(PipelineRun).where(PipelineRun.id == run_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_pipeline_runs(
    session: AsyncSession, status: str | None = None, limit: int = 20, offset: int = 0
) -> list[PipelineRun]:
    """Return pipeline runs with optional status filter and pagination.

    Args:
        session: Async database session.
        status: Optional status filter.
        limit: Maximum rows to return.
        offset: Number of rows to skip.

    Returns:
        List of :class:`PipelineRun` rows ordered newest-first.

    """
    stmt = (
        select(PipelineRun)
        .order_by(PipelineRun.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if status:
        stmt = stmt.where(PipelineRun.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_pipeline_runs(session: AsyncSession, status: str | None = None) -> int:
    """Count pipeline runs, optionally filtered by status.

    Args:
        session: Async database session.
        status: Optional status filter.

    Returns:
        Total count of matching rows.

    """
    stmt = select(sa_func.count()).select_from(PipelineRun)
    if status:
        stmt = stmt.where(PipelineRun.status == status)
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_pipeline_run_detail(session: AsyncSession, run_id) -> dict | None:
    """Fetch a pipeline run with eager-loaded OCR and post-processing results.

    Args:
        session: Async database session.
        run_id: UUID of the pipeline run.

    Returns:
        A dict representation of the run with nested results, or ``None``.

    """
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
    run = result.scalar_one_or_none()
    if not run:
        return None
    return {
        "id": run.id,
        "input_image_path": run.input_image_path,
        "status": run.status,
        "error_message": run.error_message,
        "created_at": run.created_at,
        "completed_at": run.completed_at,
        "ocr_results": [
            {
                "id": ocr.id,
                "model_name": ocr.model_name,
                "raw_text": ocr.raw_text,
                "confidence": ocr.confidence,
                "processing_time_ms": ocr.processing_time_ms,
                "error": ocr.error,
                "created_at": ocr.created_at,
                "post_processing_results": [
                    {
                        "id": pp.id,
                        "title_en": pp.title_en,
                        "title_ja": pp.title_ja,
                        "code": pp.code,
                        "confidence": pp.confidence,
                        "processing_type": pp.processing_type,
                        "created_at": pp.created_at,
                    }
                    for pp in ocr.post_processing_results
                ],
            }
            for ocr in run.ocr_results
        ],
    }


async def get_catalog_entry(session: AsyncSession, entry_id) -> CatalogEntry | None:
    """Fetch a single catalog entry by its ID.

    Args:
        session: Async database session.
        entry_id: UUID of the catalog entry.

    Returns:
        The matching :class:`CatalogEntry` or ``None``.

    """
    stmt = select(CatalogEntry).where(CatalogEntry.id == entry_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_catalog_entries(
    session: AsyncSession, status: str | None = None, limit: int = 50, offset: int = 0
) -> list[CatalogEntry]:
    """Return catalog entries with optional status filter and pagination.

    Args:
        session: Async database session.
        status: Optional status filter.
        limit: Maximum rows to return.
        offset: Number of rows to skip.

    Returns:
        List of :class:`CatalogEntry` rows ordered newest-first.

    """
    stmt = (
        select(CatalogEntry)
        .order_by(CatalogEntry.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if status:
        stmt = stmt.where(CatalogEntry.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_catalog_entries(
    session: AsyncSession, status: str | None = None
) -> int:
    """Count catalog entries, optionally filtered by status.

    Args:
        session: Async database session.
        status: Optional status filter.

    Returns:
        Total count of matching rows.

    """
    stmt = select(sa_func.count()).select_from(CatalogEntry)
    if status:
        stmt = stmt.where(CatalogEntry.status == status)
    result = await session.execute(stmt)
    return result.scalar_one()


async def update_catalog_entry(
    session: AsyncSession, entry_id: uuid.UUID, **kwargs
) -> CatalogEntry | None:
    """Update fields on an existing catalog entry.

    Args:
        session: Async database session.
        entry_id: UUID of the catalog entry.
        **kwargs: Fields to update.

    Returns:
        The updated :class:`CatalogEntry` or ``None`` if not found.

    """
    entry = await get_catalog_entry(session, entry_id)
    if not entry:
        return None
    for key, value in kwargs.items():
        if hasattr(entry, key):
            setattr(entry, key, value)
    await session.flush()
    await session.refresh(entry)
    return entry


async def get_catalog_entry_by_run(
    session: AsyncSession, run_id: uuid.UUID
) -> CatalogEntry | None:
    """Find the catalog entry associated with a pipeline run.

    Args:
        session: Async database session.
        run_id: UUID of the source pipeline run.

    Returns:
        The matching :class:`CatalogEntry` or ``None``.

    """
    stmt = select(CatalogEntry).where(CatalogEntry.source_run_id == run_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_batch_run(
    session: AsyncSession, *, name: str | None, total_count: int, **kwargs
) -> BatchRun:
    """Insert a new batch run record.

    Args:
        session: Async database session.
        name: Optional human-readable name for the batch.
        total_count: Total number of pipeline runs in this batch.
        **kwargs: Additional column values.

    Returns:
        The freshly created :class:`BatchRun`.

    """
    batch = BatchRun(name=name, total_count=total_count, **kwargs)
    session.add(batch)
    await session.flush()
    await session.refresh(batch)
    return batch


async def get_batch_run(session: AsyncSession, batch_id: uuid.UUID) -> BatchRun | None:
    """Fetch a single batch run by its ID.

    Args:
        session: Async database session.
        batch_id: UUID of the batch run.

    Returns:
        The matching :class:`BatchRun` or ``None``.

    """
    stmt = select(BatchRun).where(BatchRun.id == batch_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_batch_runs(
    session: AsyncSession,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[BatchRun]:
    """Return batch runs with optional status filter and pagination.

    Args:
        session: Async database session.
        status: Optional status filter.
        limit: Maximum rows to return.
        offset: Number of rows to skip.

    Returns:
        List of :class:`BatchRun` rows ordered newest-first.

    """
    stmt = (
        select(BatchRun)
        .order_by(BatchRun.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if status:
        stmt = stmt.where(BatchRun.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_batch_runs(session: AsyncSession, status: str | None = None) -> int:
    """Count batch runs, optionally filtered by status.

    Args:
        session: Async database session.
        status: Optional status filter.

    Returns:
        Total count of matching rows.

    """
    stmt = select(sa_func.count()).select_from(BatchRun)
    if status:
        stmt = stmt.where(BatchRun.status == status)
    result = await session.execute(stmt)
    return result.scalar_one()


async def update_batch_run(
    session: AsyncSession, batch_id: uuid.UUID, **kwargs
) -> BatchRun | None:
    """Update fields on an existing batch run.

    Args:
        session: Async database session.
        batch_id: UUID of the batch run.
        **kwargs: Fields to update.

    Returns:
        The updated :class:`BatchRun` or ``None`` if not found.

    """
    batch = await get_batch_run(session, batch_id)
    if not batch:
        return None
    for key, value in kwargs.items():
        if hasattr(batch, key):
            setattr(batch, key, value)
    await session.flush()
    await session.refresh(batch)
    return batch


async def update_batch_progress(
    session: AsyncSession, batch_id: uuid.UUID
) -> BatchRun | None:
    """Recalculate counters and status for a batch run after a child run finishes.

    Counts completed/failed child runs, updates the counters, and sets the
    final batch status (``completed``, ``partial_failure``, or leaves as
    ``processing``).

    Args:
        session: Async database session.
        batch_id: UUID of the batch run to update.

    Returns:
        The updated :class:`BatchRun` or ``None`` if not found.

    """
    batch = await get_batch_run(session, batch_id)
    if not batch:
        return None

    completed = (
        await session.execute(
            select(sa_func.count())
            .select_from(PipelineRun)
            .where(
                PipelineRun.batch_run_id == batch_id,
                PipelineRun.status == "completed",
            )
        )
    ).scalar_one()

    failed = (
        await session.execute(
            select(sa_func.count())
            .select_from(PipelineRun)
            .where(
                PipelineRun.batch_run_id == batch_id,
                PipelineRun.status == "failed",
            )
        )
    ).scalar_one()

    batch.completed_count = completed
    batch.failed_count = failed

    finished = completed + failed
    if finished >= batch.total_count:
        if failed == 0:
            batch.status = "completed"
        else:
            batch.status = "partial_failure"
        batch.completed_at = datetime.now(UTC).replace(tzinfo=None)

    await session.flush()
    await session.refresh(batch)
    return batch


async def _unset_default_profiles(session: AsyncSession) -> None:
    stmt = (
        PipelineProfile.__table__.update()
        .where(PipelineProfile.is_default.is_(True))
        .values(is_default=False)
    )
    await session.execute(stmt)


async def create_profile(
    session: AsyncSession,
    *,
    name: str,
    description: str | None = None,
    preprocess_steps: dict | None = None,
    ocr_models: dict | None = None,
    enable_llm: bool = False,
    is_default: bool = False,
) -> PipelineProfile:
    if is_default:
        await _unset_default_profiles(session)
    profile = PipelineProfile(
        name=name,
        description=description,
        preprocess_steps=preprocess_steps,
        ocr_models=ocr_models,
        enable_llm=enable_llm,
        is_default=is_default,
    )
    session.add(profile)
    await session.flush()
    await session.refresh(profile)
    return profile


async def get_profile(
    session: AsyncSession, profile_id: uuid.UUID
) -> PipelineProfile | None:
    stmt = select(PipelineProfile).where(PipelineProfile.id == profile_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_default_profile(session: AsyncSession) -> PipelineProfile | None:
    stmt = select(PipelineProfile).where(PipelineProfile.is_default.is_(True))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_profiles(
    session: AsyncSession, limit: int = 50, offset: int = 0
) -> list[PipelineProfile]:
    stmt = (
        select(PipelineProfile)
        .order_by(PipelineProfile.name)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_profiles(session: AsyncSession) -> int:
    stmt = select(sa_func.count()).select_from(PipelineProfile)
    result = await session.execute(stmt)
    return result.scalar_one()


async def update_profile(
    session: AsyncSession, profile_id: uuid.UUID, **kwargs
) -> PipelineProfile | None:
    profile = await get_profile(session, profile_id)
    if not profile:
        return None
    if kwargs.get("is_default") is True:
        await _unset_default_profiles(session)
    for key, value in kwargs.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    await session.flush()
    await session.refresh(profile)
    return profile


async def delete_profile(
    session: AsyncSession, profile_id: uuid.UUID
) -> bool:
    profile = await get_profile(session, profile_id)
    if not profile:
        return False
    await session.delete(profile)
    await session.flush()
    return True
