"""Pipeline result persistence — shared by worker and future direct-run endpoints."""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.db.enums import CatalogStatus
from ocr_manga_title.db.models import (
    CatalogEntry,
    OCRResult as OCRResultDB,
    PostProcessingResult,
)
from ocr_manga_title.schemas import PipelineResult

logger = logging.getLogger(__name__)

_OVERWRITABLE_FIELDS = ("title_en", "title_ja", "code")


def _apply_field_updates(
    target: Any,
    updates: dict[str, Any],
    fields: tuple[str, ...] = _OVERWRITABLE_FIELDS,
) -> None:
    for f in fields:
        if updates.get(f) is not None:
            setattr(target, f, updates[f])


async def _persist_ocr_results(
    session: AsyncSession,
    run_id: uuid.UUID,
    ocr_results: list[Any],
) -> None:
    for ocr_result in ocr_results:
        blocks_data = (
            [b.model_dump() for b in ocr_result.blocks] if ocr_result.blocks else None
        )
        session.add(
            OCRResultDB(
                pipeline_run_id=run_id,
                model_name=ocr_result.model_name,
                raw_text=ocr_result.raw_text,
                confidence=ocr_result.confidence,
                processing_time_ms=ocr_result.processing_time_ms,
                error=ocr_result.error,
                blocks=blocks_data,
            )
        )
    await session.flush()


async def _find_ocr_db(
    session: AsyncSession,
    run_id: uuid.UUID,
    model_name: str,
) -> OCRResultDB | None:
    stmt = select(OCRResultDB).where(
        OCRResultDB.pipeline_run_id == run_id,
        OCRResultDB.model_name == model_name,
    )
    r = await session.execute(stmt)
    return r.scalars().first()


async def _persist_postprocessing(
    session: AsyncSession,
    run_id: uuid.UUID,
    pipeline_result: PipelineResult,
    llm_config: dict[str, Any] | None,
) -> None:
    extracted = pipeline_result.extracted
    if not extracted:
        return

    source = next(
        (
            o
            for o in pipeline_result.ocr_results
            if o.model_name == extracted.source_model
        ),
        None,
    )
    if source is None:
        return

    found_ocr = await _find_ocr_db(session, run_id, source.model_name)
    if found_ocr is None:
        return

    pp_kwargs: dict[str, Any] = {
        "ocr_result_id": found_ocr.id,
        "title_en": extracted.title_en,
        "title_ja": extracted.title_ja,
        "code": extracted.code,
        "confidence": extracted.confidence,
        "processing_type": extracted.source_method or "unknown",
        "raw_response": extracted.raw_response,
        "extra_metadata": extracted.extra_metadata,
    }
    if llm_config:
        pp_kwargs["system_prompt_used"] = llm_config.get("system_prompt", "")
        pp_kwargs["user_prompt_used"] = llm_config.get(
            "user_prompt_template", "{ocr_text}"
        )
        pp_kwargs["temperature_used"] = float(llm_config.get("temperature", 0.1))
    session.add(PostProcessingResult(**pp_kwargs))

    if extracted.confidence > 0.0:
        session.add(
            CatalogEntry(
                source_run_id=run_id,
                title_en=extracted.title_en,
                title_ja=extracted.title_ja,
                code=extracted.code,
                confidence=extracted.confidence,
            )
        )


async def save_pipeline_results(
    session: AsyncSession,
    run_id: uuid.UUID,
    pipeline_result: PipelineResult,
    *,
    llm_config: dict[str, Any] | None = None,
) -> None:
    """Persist OCR results, post-processing results, and catalog entry."""
    await _persist_ocr_results(session, run_id, pipeline_result.ocr_results)
    await _persist_postprocessing(session, run_id, pipeline_result, llm_config)


async def override_and_sync(
    session: AsyncSession,
    result_id: uuid.UUID,
    updates: dict[str, Any],
) -> PostProcessingResult | None:
    """Override post-processing result fields and propagate to catalog."""
    from ocr_manga_title.db.crud import get_catalog_entry_by_run

    stmt = select(PostProcessingResult).where(PostProcessingResult.id == result_id)
    result = await session.execute(stmt)
    pp_result = result.scalar_one_or_none()
    if not pp_result:
        return None

    _apply_field_updates(pp_result, updates)
    await session.flush()

    stmt_ocr = select(OCRResultDB).where(OCRResultDB.id == pp_result.ocr_result_id)
    ocr_result = (await session.execute(stmt_ocr)).scalar_one_or_none()
    if ocr_result is None:
        logger.warning(
            "OCR result not found for pp_result.ocr_result_id=%s",
            pp_result.ocr_result_id,
        )
        return None
    catalog = await get_catalog_entry_by_run(session, ocr_result.pipeline_run_id)
    if catalog:
        _apply_field_updates(catalog, updates)
        catalog.status = CatalogStatus.NEEDS_REVIEW
        await session.flush()

    await session.refresh(pp_result)
    return pp_result
