import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ocr_manga_title.db.models import (
    CatalogEntry,
    ModelConfig,
    OCRResult,
    PipelineRun,
    PostProcessingResult,
    PromptVersion,
)


async def test_pipeline_run_defaults(db_session):
    run = PipelineRun(input_image_path="/test/image.png")
    db_session.add(run)
    await db_session.flush()

    assert isinstance(run.id, uuid.UUID)
    assert run.status == "pending"
    assert run.error_message is None
    assert run.preprocess_config is None
    assert run.completed_at is None
    assert run.created_at is not None


async def test_pipeline_run_with_all_fields(db_session):
    run = PipelineRun(
        input_image_path="/test/image.png",
        source_url="https://example.com/img.jpg",
        source_platform="twitter",
        status="completed",
        preprocess_config={"enabled": True},
    )
    db_session.add(run)
    await db_session.flush()

    assert run.source_url == "https://example.com/img.jpg"
    assert run.source_platform == "twitter"
    assert run.status == "completed"


async def test_ocr_result_relationship(db_session):
    run = PipelineRun(input_image_path="/test/image.png")
    db_session.add(run)
    await db_session.flush()

    ocr = OCRResult(
        pipeline_run_id=run.id,
        model_name="tesseract",
        raw_text="test text",
        confidence=0.85,
        processing_time_ms=150,
    )
    db_session.add(ocr)
    await db_session.flush()

    assert ocr.pipeline_run_id == run.id
    assert ocr.model_name == "tesseract"
    assert ocr.created_at is not None

    stmt = (
        select(PipelineRun)
        .options(selectinload(PipelineRun.ocr_results))
        .where(PipelineRun.id == run.id)
    )
    result = await db_session.execute(stmt)
    refreshed_run = result.scalar_one()
    assert len(refreshed_run.ocr_results) == 1
    assert refreshed_run.ocr_results[0].raw_text == "test text"


async def test_post_processing_result(db_session):
    run = PipelineRun(input_image_path="/test/image.png")
    db_session.add(run)
    await db_session.flush()

    ocr = OCRResult(
        pipeline_run_id=run.id,
        model_name="tesseract",
        raw_text="One Piece",
        confidence=0.9,
        processing_time_ms=100,
    )
    db_session.add(ocr)
    await db_session.flush()

    pp = PostProcessingResult(
        ocr_result_id=ocr.id,
        title_en="One Piece",
        confidence=0.95,
        processing_type="llm",
    )
    db_session.add(pp)
    await db_session.flush()

    assert pp.title_en == "One Piece"
    assert pp.processing_type == "llm"

    stmt = (
        select(OCRResult)
        .options(selectinload(OCRResult.post_processing_results))
        .where(OCRResult.id == ocr.id)
    )
    result = await db_session.execute(stmt)
    refreshed_ocr = result.scalar_one()
    assert len(refreshed_ocr.post_processing_results) == 1


async def test_prompt_version(db_session):
    pv = PromptVersion(
        prompt_type="llm",
        content="Extract the title",
        version_number=1,
        is_active=True,
        tags="extraction,v1",
    )
    db_session.add(pv)
    await db_session.flush()

    assert isinstance(pv.id, uuid.UUID)
    assert pv.prompt_type == "llm"
    assert pv.is_active is True
    assert pv.created_at is not None


async def test_prompt_version_default_inactive(db_session):
    pv = PromptVersion(
        prompt_type="llm",
        content="test",
        version_number=2,
    )
    db_session.add(pv)
    await db_session.flush()

    assert pv.is_active is False


async def test_catalog_entry(db_session):
    run = PipelineRun(input_image_path="/test/image.png")
    db_session.add(run)
    await db_session.flush()

    entry = CatalogEntry(
        title_en="Naruto",
        title_ja="ナルト",
        code="978-1-56931-900-0",
        source_run_id=run.id,
        confidence=0.92,
    )
    db_session.add(entry)
    await db_session.flush()

    assert isinstance(entry.id, uuid.UUID)
    assert entry.status == "needs_review"
    assert entry.source_run_id == run.id

    stmt = (
        select(PipelineRun)
        .options(selectinload(PipelineRun.catalog_entries))
        .where(PipelineRun.id == run.id)
    )
    result = await db_session.execute(stmt)
    refreshed_run = result.scalar_one()
    assert len(refreshed_run.catalog_entries) == 1


async def test_model_config(db_session):
    mc = ModelConfig(
        model_name="tesseract",
        is_enabled=True,
        parameters={"languages": ["eng", "jpn"]},
        language_hint="eng+jpn",
    )
    db_session.add(mc)
    await db_session.flush()

    assert isinstance(mc.id, uuid.UUID)
    assert mc.is_enabled is True
    assert mc.updated_at is not None


async def test_model_config_default_enabled(db_session):
    mc = ModelConfig(model_name="test_model")
    db_session.add(mc)
    await db_session.flush()

    assert mc.is_enabled is True


async def test_model_config_unique_name(db_session):
    mc1 = ModelConfig(model_name="unique_model")
    db_session.add(mc1)
    await db_session.flush()

    mc2 = ModelConfig(model_name="unique_model")
    db_session.add(mc2)
    with pytest.raises(Exception):
        await db_session.flush()


async def test_cascade_delete_pipeline_run(db_session):
    run = PipelineRun(input_image_path="/test/image.png")
    db_session.add(run)
    await db_session.flush()

    ocr = OCRResult(
        pipeline_run_id=run.id,
        model_name="tesseract",
        raw_text="text",
        confidence=0.5,
        processing_time_ms=100,
    )
    db_session.add(ocr)
    await db_session.flush()

    pp = PostProcessingResult(
        ocr_result_id=ocr.id,
        confidence=0.9,
        processing_type="rules",
    )
    db_session.add(pp)
    await db_session.flush()

    pp_id = pp.id
    ocr_id = ocr.id

    await db_session.delete(run)
    await db_session.flush()

    assert (await db_session.get(OCRResult, ocr_id)) is None
    assert (await db_session.get(PostProcessingResult, pp_id)) is None
