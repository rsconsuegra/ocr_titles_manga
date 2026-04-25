import uuid
from unittest.mock import patch

from ocr_manga_title.db.crud import create_pipeline_run
from ocr_manga_title.db.models import OCRResult, PostProcessingResult


async def test_trigger_pipeline_enqueues_job(client, db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        run = await create_pipeline_run(
            session=session, input_image_path="test.png", source_platform="manual"
        )
        run_id = str(run.id)
        await session.commit()

    with patch("ocr_manga_title.workers.ocr_worker.process_pipeline_run") as mock_actor:
        mock_actor.send = lambda *a, **kw: None
        response = await client.post(f"/api/v1/pipeline/run/{run_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Pipeline run enqueued"
    assert data["run_id"] == run_id


async def test_trigger_pipeline_not_found(client):
    random_id = str(uuid.uuid4())
    with patch("ocr_manga_title.workers.ocr_worker.process_pipeline_run") as mock_actor:
        mock_actor.send = lambda *a, **kw: None
        response = await client.post(f"/api/v1/pipeline/run/{random_id}")

    assert response.status_code == 404


async def test_trigger_pipeline_already_completed(client, db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        run = await create_pipeline_run(
            session=session,
            input_image_path="test.png",
            source_platform="manual",
            status="completed",
        )
        run_id = str(run.id)
        await session.commit()

    with patch("ocr_manga_title.workers.ocr_worker.process_pipeline_run") as mock_actor:
        mock_actor.send = lambda *a, **kw: None
        response = await client.post(f"/api/v1/pipeline/run/{run_id}")

    assert response.status_code == 200


async def test_trigger_pipeline_processing_rejected(client, db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        run = await create_pipeline_run(
            session=session,
            input_image_path="test.png",
            source_platform="manual",
            status="processing",
        )
        run_id = str(run.id)
        await session.commit()

    response = await client.post(f"/api/v1/pipeline/run/{run_id}")
    assert response.status_code == 409


async def test_cancel_pipeline_run_pending(client, db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        run = await create_pipeline_run(
            session=session,
            input_image_path="test.png",
            source_platform="manual",
            status="pending",
        )
        run_id = str(run.id)
        await session.commit()

    response = await client.post(f"/api/v1/pipeline/runs/{run_id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Pipeline run cancelled"
    assert data["run_id"] == run_id

    detail = await client.get(f"/api/v1/pipeline/runs/{run_id}")
    assert detail.json()["status"] == "cancelled"


async def test_cancel_pipeline_run_completed_rejected(client, db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        run = await create_pipeline_run(
            session=session,
            input_image_path="test.png",
            source_platform="manual",
            status="completed",
        )
        run_id = str(run.id)
        await session.commit()

    response = await client.post(f"/api/v1/pipeline/runs/{run_id}/cancel")
    assert response.status_code == 409


async def test_cancel_pipeline_run_not_found(client):
    random_id = str(uuid.uuid4())
    response = await client.post(f"/api/v1/pipeline/runs/{random_id}/cancel")
    assert response.status_code == 404


async def test_retry_cancelled_run(client, db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        run = await create_pipeline_run(
            session=session,
            input_image_path="test.png",
            source_platform="manual",
            status="cancelled",
        )
        run_id = str(run.id)
        await session.commit()

    with patch("ocr_manga_title.workers.ocr_worker.process_pipeline_run") as mock_actor:
        mock_actor.send = lambda *a, **kw: None
        response = await client.post(f"/api/v1/pipeline/run/{run_id}")

    assert response.status_code == 200


async def test_list_runs_empty(client):
    response = await client.get("/api/v1/pipeline/runs")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["limit"] == 20
    assert data["offset"] == 0


async def test_list_runs_with_data(client, db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        for i in range(5):
            status = "completed" if i < 3 else "pending"
            await create_pipeline_run(
                session=session, input_image_path=f"test_{i}.png", status=status
            )
        await session.commit()

    response = await client.get("/api/v1/pipeline/runs")
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5


async def test_list_runs_filter_by_status(client, db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        for status in ["completed", "completed", "pending"]:
            await create_pipeline_run(
                session=session, input_image_path="test.png", status=status
            )
        await session.commit()

    response = await client.get("/api/v1/pipeline/runs?status=completed")
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert all(item["status"] == "completed" for item in data["items"])


async def test_list_runs_pagination(client, db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        for i in range(25):
            await create_pipeline_run(session=session, input_image_path=f"test_{i}.png")
        await session.commit()

    response = await client.get("/api/v1/pipeline/runs?limit=10&offset=0")
    data = response.json()
    assert data["total"] == 25
    assert len(data["items"]) == 10

    response = await client.get("/api/v1/pipeline/runs?limit=10&offset=20")
    data = response.json()
    assert data["total"] == 25
    assert len(data["items"]) == 5


async def test_get_run_detail_pending(client, db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        run = await create_pipeline_run(session=session, input_image_path="test.png")
        run_id = str(run.id)
        await session.commit()

    response = await client.get(f"/api/v1/pipeline/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["ocr_results"] == []


async def test_get_run_detail_with_results(client, db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        run = await create_pipeline_run(session=session, input_image_path="test.png")
        await session.flush()

        ocr = OCRResult(
            pipeline_run_id=run.id,
            model_name="tesseract",
            raw_text="One Piece",
            confidence=0.85,
            processing_time_ms=100,
        )
        session.add(ocr)
        await session.flush()

        pp = PostProcessingResult(
            ocr_result_id=ocr.id,
            title_en="One Piece",
            confidence=0.9,
            processing_type="llm",
        )
        session.add(pp)
        await session.commit()
        run_id = str(run.id)

    response = await client.get(f"/api/v1/pipeline/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert len(data["ocr_results"]) == 1
    assert data["ocr_results"][0]["model_name"] == "tesseract"
    assert data["ocr_results"][0]["raw_text"] == "One Piece"
    assert len(data["ocr_results"][0]["post_processing_results"]) == 1
    assert (
        data["ocr_results"][0]["post_processing_results"][0]["title_en"] == "One Piece"
    )


async def test_get_run_detail_not_found(client):
    random_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/pipeline/runs/{random_id}")
    assert response.status_code == 404


async def test_get_run_detail_multiple_ocr_results(client, db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        run = await create_pipeline_run(session=session, input_image_path="test.png")
        await session.flush()

        for model in ["tesseract", "paddle"]:
            ocr = OCRResult(
                pipeline_run_id=run.id,
                model_name=model,
                raw_text=f"text from {model}",
                confidence=0.8,
                processing_time_ms=100,
            )
            session.add(ocr)
        await session.commit()
        run_id = str(run.id)

    response = await client.get(f"/api/v1/pipeline/runs/{run_id}")
    data = response.json()
    assert len(data["ocr_results"]) == 2
    model_names = {r["model_name"] for r in data["ocr_results"]}
    assert model_names == {"tesseract", "paddle"}
