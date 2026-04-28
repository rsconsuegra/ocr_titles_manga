import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ocr_manga_title.db.crud import create_pipeline_run
from ocr_manga_title.db.models import (
    CatalogEntry,
    ModelConfig,
    OCRResult as OCRResultDB,
    PostProcessingResult,
    PromptVersion,
)
from ocr_manga_title.schemas import (
    ExtractedTitle,
    ModelConfig as ModelConfigSchema,
    OCRResult as OCRResultSchema,
    PipelineResult,
)
from ocr_manga_title.workers.ocr_worker import (
    _get_model_configs,
    _process,
)


def _fake_pipeline_result(ocr_results=None, extracted=None):
    return PipelineResult(
        input_path="test.png",
        ocr_results=ocr_results
        or [
            OCRResultSchema(
                model_name="tesseract",
                raw_text="One Piece",
                confidence=0.85,
                processing_time_ms=100,
            )
        ],
        extracted=extracted
        or ExtractedTitle(
            title_en="One Piece",
            title_ja="ワンピース",
            code="OP",
            confidence=0.9,
            source_model="tesseract",
            source_method="llm",
        ),
    )


async def _seed_model_config(session, model_name="tesseract", enabled=True):
    config = ModelConfig(
        model_name=model_name,
        is_enabled=enabled,
        language_hint="eng",
        parameters={"psm": "6"},
    )
    session.add(config)
    await session.flush()


async def _seed_prompt(session):
    prompt = PromptVersion(
        prompt_type="llm",
        content="Extract title from: {text}",
        version_number=1,
        is_active=True,
    )
    session.add(prompt)
    await session.flush()


async def test_successful_pipeline_run(db_engine, tmp_path):
    test_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    async with test_factory() as session:
        run = await create_pipeline_run(session=session, input_image_path=str(img))
        await _seed_model_config(session)
        await _seed_prompt(session)
        await session.commit()
        run_id = str(run.id)

    with (
        patch("ocr_manga_title.workers.ocr_worker.OCREngine") as mock_engine_cls,
        patch("ocr_manga_title.workers.ocr_worker.load_config") as mock_load_config,
        patch(
            "ocr_manga_title.workers.ocr_worker.load_preprocess_config"
        ) as mock_pp_config,
    ):
        mock_load_config.return_value = MagicMock()
        mock_pp_config.return_value = {"preprocessing": {"enabled": False}}
        mock_engine_instance = MagicMock()
        mock_engine_instance.process.return_value = _fake_pipeline_result()
        mock_engine_cls.return_value = mock_engine_instance

        await _process(run_id, test_factory)

    async with test_factory() as session:
        stmt = select(OCRResultDB).where(
            OCRResultDB.pipeline_run_id == uuid.UUID(run_id)
        )
        result = await session.execute(stmt)
        ocr_results = list(result.scalars().all())
        assert len(ocr_results) == 1
        assert ocr_results[0].model_name == "tesseract"
        assert ocr_results[0].raw_text == "One Piece"
        assert ocr_results[0].confidence == 0.85

        stmt2 = select(PostProcessingResult)
        result2 = await session.execute(stmt2)
        pp_results = list(result2.scalars().all())
        assert len(pp_results) == 1
        assert pp_results[0].title_en == "One Piece"
        assert pp_results[0].title_ja == "ワンピース"
        assert pp_results[0].processing_type == "llm"

        from ocr_manga_title.db.models import PipelineRun

        stmt3 = select(PipelineRun).where(PipelineRun.id == uuid.UUID(run_id))
        r3 = await session.execute(stmt3)
        run = r3.scalar_one()
        assert run.status == "completed"
        assert run.completed_at is not None


async def test_catalog_entry_created_when_confidence_above_zero(db_engine, tmp_path):
    test_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    async with test_factory() as session:
        run = await create_pipeline_run(session=session, input_image_path=str(img))
        await _seed_model_config(session)
        await session.commit()
        run_id = str(run.id)

    with (
        patch("ocr_manga_title.workers.ocr_worker.OCREngine") as mock_engine_cls,
        patch("ocr_manga_title.workers.ocr_worker.load_config") as mock_load_config,
        patch(
            "ocr_manga_title.workers.ocr_worker.load_preprocess_config"
        ) as mock_pp_config,
    ):
        mock_load_config.return_value = MagicMock()
        mock_pp_config.return_value = {"preprocessing": {"enabled": False}}
        mock_engine_instance = MagicMock()
        mock_engine_instance.process.return_value = _fake_pipeline_result()
        mock_engine_cls.return_value = mock_engine_instance

        await _process(run_id, test_factory)

    async with test_factory() as session:
        stmt = select(CatalogEntry).where(
            CatalogEntry.source_run_id == uuid.UUID(run_id)
        )
        result = await session.execute(stmt)
        entries = list(result.scalars().all())
        assert len(entries) == 1
        assert entries[0].title_en == "One Piece"
        assert entries[0].confidence == 0.9


async def test_no_catalog_entry_when_confidence_zero(db_engine, tmp_path):
    test_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    async with test_factory() as session:
        run = await create_pipeline_run(session=session, input_image_path=str(img))
        await _seed_model_config(session)
        await session.commit()
        run_id = str(run.id)

    with (
        patch("ocr_manga_title.workers.ocr_worker.OCREngine") as mock_engine_cls,
        patch("ocr_manga_title.workers.ocr_worker.load_config") as mock_load_config,
        patch(
            "ocr_manga_title.workers.ocr_worker.load_preprocess_config"
        ) as mock_pp_config,
    ):
        mock_load_config.return_value = MagicMock()
        mock_pp_config.return_value = {"preprocessing": {"enabled": False}}
        mock_engine_instance = MagicMock()
        mock_engine_instance.process.return_value = _fake_pipeline_result(
            extracted=ExtractedTitle(
                title_en="Unknown",
                confidence=0.0,
                source_model="tesseract",
                source_method="rule",
            ),
        )
        mock_engine_cls.return_value = mock_engine_instance

        await _process(run_id, test_factory)

    async with test_factory() as session:
        stmt = select(CatalogEntry).where(
            CatalogEntry.source_run_id == uuid.UUID(run_id)
        )
        result = await session.execute(stmt)
        entries = list(result.scalars().all())
        assert len(entries) == 0


async def test_failed_pipeline_engine_raises(db_engine, tmp_path):
    test_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    async with test_factory() as session:
        run = await create_pipeline_run(session=session, input_image_path=str(img))
        await _seed_model_config(session)
        await session.commit()
        run_id = str(run.id)

    with (
        patch("ocr_manga_title.workers.ocr_worker.OCREngine") as mock_engine_cls,
        patch("ocr_manga_title.workers.ocr_worker.load_config") as mock_load_config,
        patch(
            "ocr_manga_title.workers.ocr_worker.load_preprocess_config"
        ) as mock_pp_config,
    ):
        mock_load_config.return_value = MagicMock()
        mock_pp_config.return_value = {"preprocessing": {"enabled": False}}
        mock_engine_instance = MagicMock()
        mock_engine_instance.process.side_effect = ConnectionError("LLM timeout")
        mock_engine_cls.return_value = mock_engine_instance

        with pytest.raises(ConnectionError, match="LLM timeout"):
            await _process(run_id, test_factory)

    async with test_factory() as session:
        from ocr_manga_title.db.models import PipelineRun

        stmt = select(PipelineRun).where(PipelineRun.id == uuid.UUID(run_id))
        result = await session.execute(stmt)
        run = result.scalar_one()
        assert run.status == "failed"
        assert "LLM timeout" in run.error_message


async def test_missing_run_id(db_engine):
    test_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    await _process(str(uuid.uuid4()), test_factory)


async def test_invalid_run_id_format(db_engine):
    test_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    await _process("not-a-uuid", test_factory)


async def test_model_config_loaded_from_db(db_engine, tmp_path):
    test_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    async with test_factory() as session:
        run = await create_pipeline_run(session=session, input_image_path=str(img))
        await _seed_model_config(session, "tesseract", enabled=True)
        await _seed_model_config(session, "paddle", enabled=False)
        await session.commit()
        run_id = str(run.id)

    captured_configs = {}

    def capture_engine_init(config, ocr_config, preprocess_config=None, llm_config=None):
        captured_configs.update(ocr_config)
        mock = MagicMock()
        mock.process.return_value = _fake_pipeline_result()
        return mock

    with (
        patch(
            "ocr_manga_title.workers.ocr_worker.OCREngine",
            side_effect=capture_engine_init,
        ),
        patch("ocr_manga_title.workers.ocr_worker.load_config") as mock_load_config,
        patch(
            "ocr_manga_title.workers.ocr_worker.load_preprocess_config"
        ) as mock_pp_config,
    ):
        mock_load_config.return_value = MagicMock()
        mock_pp_config.return_value = {"preprocessing": {"enabled": False}}

        await _process(run_id, test_factory)

    assert "tesseract" in captured_configs
    assert "paddle" not in captured_configs
    assert captured_configs["tesseract"].name == "tesseract"
    assert captured_configs["tesseract"].enabled is True


async def test_permanent_error_no_retry(db_engine, tmp_path):
    test_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    img = tmp_path / "nonexistent.png"

    async with test_factory() as session:
        run = await create_pipeline_run(session=session, input_image_path=str(img))
        await _seed_model_config(session)
        await session.commit()
        run_id = str(run.id)

    await _process(run_id, test_factory)

    async with test_factory() as session:
        from ocr_manga_title.db.models import PipelineRun

        stmt = select(PipelineRun).where(PipelineRun.id == uuid.UUID(run_id))
        result = await session.execute(stmt)
        run = result.scalar_one()
        assert run.status == "failed"
        assert "Image not found" in run.error_message


async def test_transient_error_re_raised_for_retry(db_engine, tmp_path):
    test_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    async with test_factory() as session:
        run = await create_pipeline_run(session=session, input_image_path=str(img))
        await _seed_model_config(session)
        await session.commit()
        run_id = str(run.id)

    with (
        patch("ocr_manga_title.workers.ocr_worker.OCREngine") as mock_engine_cls,
        patch("ocr_manga_title.workers.ocr_worker.load_config") as mock_load_config,
        patch(
            "ocr_manga_title.workers.ocr_worker.load_preprocess_config"
        ) as mock_pp_config,
    ):
        mock_load_config.return_value = MagicMock()
        mock_pp_config.return_value = {"preprocessing": {"enabled": False}}
        mock_engine_instance = MagicMock()
        mock_engine_instance.process.side_effect = TimeoutError("connection timed out")
        mock_engine_cls.return_value = mock_engine_instance

        with pytest.raises(TimeoutError, match="connection timed out"):
            await _process(run_id, test_factory)

    async with test_factory() as session:
        from ocr_manga_title.db.models import PipelineRun

        stmt = select(PipelineRun).where(PipelineRun.id == uuid.UUID(run_id))
        result = await session.execute(stmt)
        run = result.scalar_one()
        assert run.status == "failed"
        assert "connection timed out" in run.error_message


async def test_get_model_configs_returns_enabled_only(db_session):
    await _seed_model_config(db_session, "tesseract", enabled=True)
    await _seed_model_config(db_session, "paddle", enabled=False)
    await db_session.commit()

    configs = await _get_model_configs(db_session)
    assert "tesseract" in configs
    assert "paddle" not in configs
    assert isinstance(configs["tesseract"], ModelConfigSchema)
