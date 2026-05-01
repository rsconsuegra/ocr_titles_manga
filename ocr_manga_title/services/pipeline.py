"""Pipeline result persistence — shared by worker and future direct-run endpoints."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.db.enums import CatalogStatus
from ocr_manga_title.db.models import (
    CatalogEntry,
    OCRResult as OCRResultDB,
    PostProcessingResult,
)
from ocr_manga_title.schemas import PipelineResult


async def save_pipeline_results(
    session: AsyncSession,
    run_id: uuid.UUID,
    pipeline_result: PipelineResult,
    *,
    llm_config: dict | None = None,
) -> None:
    """Persist OCR results, post-processing results, and catalog entry."""
    for ocr_result in pipeline_result.ocr_results:
        blocks_data = None
        if ocr_result.blocks:
            blocks_data = [b.model_dump() for b in ocr_result.blocks]
        ocr_db = OCRResultDB(
            pipeline_run_id=run_id,
            model_name=ocr_result.model_name,
            raw_text=ocr_result.raw_text,
            confidence=ocr_result.confidence,
            processing_time_ms=ocr_result.processing_time_ms,
            error=ocr_result.error,
            blocks=blocks_data,
        )
        session.add(ocr_db)
        await session.flush()

    if pipeline_result.extracted:
        best_ocr = None
        for ocr_result in pipeline_result.ocr_results:
            if ocr_result.model_name == pipeline_result.extracted.source_model:
                best_ocr = ocr_result
                break

        if best_ocr:
            stmt = select(OCRResultDB).where(
                OCRResultDB.pipeline_run_id == run_id,
                OCRResultDB.model_name == best_ocr.model_name,
            )
            r = await session.execute(stmt)
            ocr_db = r.scalars().first()

            if ocr_db:
                pp_kwargs: dict = {
                    "ocr_result_id": ocr_db.id,
                    "title_en": pipeline_result.extracted.title_en,
                    "title_ja": pipeline_result.extracted.title_ja,
                    "code": pipeline_result.extracted.code,
                    "confidence": pipeline_result.extracted.confidence,
                    "processing_type": pipeline_result.extracted.source_method
                    or "unknown",
                    "raw_response": pipeline_result.extracted.raw_response,
                }
                if llm_config:
                    pp_kwargs["system_prompt_used"] = llm_config.get("system_prompt", "")
                    pp_kwargs["user_prompt_used"] = llm_config.get("user_prompt_template", "{ocr_text}")
                    pp_kwargs["temperature_used"] = float(llm_config.get("temperature", 0.1))
                pp_result = PostProcessingResult(**pp_kwargs)
                session.add(pp_result)

        if pipeline_result.extracted.confidence > 0.0:
            catalog_entry = CatalogEntry(
                source_run_id=run_id,
                title_en=pipeline_result.extracted.title_en,
                title_ja=pipeline_result.extracted.title_ja,
                code=pipeline_result.extracted.code,
                confidence=pipeline_result.extracted.confidence,
            )
            session.add(catalog_entry)


async def override_and_sync(
    session: AsyncSession,
    result_id: uuid.UUID,
    updates: dict,
) -> PostProcessingResult | None:
    """Override post-processing result fields and propagate to catalog."""
    from ocr_manga_title.db.crud import get_catalog_entry_by_run

    stmt = select(PostProcessingResult).where(PostProcessingResult.id == result_id)
    result = await session.execute(stmt)
    pp_result = result.scalar_one_or_none()
    if not pp_result:
        return None

    if updates.get("title_en") is not None:
        pp_result.title_en = updates["title_en"]
    if updates.get("title_ja") is not None:
        pp_result.title_ja = updates["title_ja"]
    if updates.get("code") is not None:
        pp_result.code = updates["code"]

    await session.flush()

    stmt_ocr = select(OCRResultDB).where(OCRResultDB.id == pp_result.ocr_result_id)
    ocr_result = (await session.execute(stmt_ocr)).scalar_one()
    catalog = await get_catalog_entry_by_run(session, ocr_result.pipeline_run_id)
    if catalog:
        if updates.get("title_en") is not None:
            catalog.title_en = updates["title_en"]
        if updates.get("title_ja") is not None:
            catalog.title_ja = updates["title_ja"]
        if updates.get("code") is not None:
            catalog.code = updates["code"]
        catalog.status = CatalogStatus.NEEDS_REVIEW
        await session.flush()

    await session.refresh(pp_result)
    return pp_result
