import uuid

from ocr_manga_title.db.crud import create_pipeline_run
from ocr_manga_title.db.models import CatalogEntry, OCRResult, PostProcessingResult


async def _seed_results(db_engine, n=3):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        pp_ids = []
        for i in range(n):
            run = await create_pipeline_run(
                session=session, input_image_path=f"test_{i}.png"
            )
            await session.flush()
            ocr = OCRResult(
                pipeline_run_id=run.id,
                model_name="tesseract" if i % 2 == 0 else "paddle",
                raw_text=f"text_{i}",
                confidence=0.5 + i * 0.15,
                processing_time_ms=100 + i * 10,
            )
            session.add(ocr)
            await session.flush()
            pp = PostProcessingResult(
                ocr_result_id=ocr.id,
                title_en=f"Title {i}",
                confidence=0.5 + i * 0.15,
                processing_type="llm",
            )
            session.add(pp)
            await session.flush()
            pp_ids.append(str(pp.id))
        await session.commit()
    return pp_ids


async def test_list_results_empty(client):
    response = await client.get("/api/v1/results")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_results_with_data(client, db_engine):
    await _seed_results(db_engine, 3)
    response = await client.get("/api/v1/results")
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


async def test_list_results_filter_by_model(client, db_engine):
    await _seed_results(db_engine, 3)
    response = await client.get("/api/v1/results?model_name=tesseract")
    data = response.json()
    assert len(data["items"]) >= 1
    assert data["total"] >= 1


async def test_list_results_filter_min_confidence(client, db_engine):
    await _seed_results(db_engine, 3)
    response = await client.get("/api/v1/results?min_confidence=0.7")
    data = response.json()
    assert all(item["confidence"] >= 0.7 for item in data["items"])


async def test_list_results_confidence_range(client, db_engine):
    await _seed_results(db_engine, 3)
    response = await client.get("/api/v1/results?min_confidence=0.5&max_confidence=0.8")
    data = response.json()
    assert all(0.5 <= item["confidence"] <= 0.8 for item in data["items"])


async def test_override_result_title(client, db_engine):
    pp_ids = await _seed_results(db_engine, 1)
    response = await client.put(
        f"/api/v1/results/{pp_ids[0]}/override",
        json={"title_en": "Overridden Title"},
    )
    assert response.status_code == 200
    assert response.json()["title_en"] == "Overridden Title"


async def test_override_result_code(client, db_engine):
    pp_ids = await _seed_results(db_engine, 1)
    response = await client.put(
        f"/api/v1/results/{pp_ids[0]}/override",
        json={"code": "978-1234567890"},
    )
    assert response.status_code == 200
    assert response.json()["code"] == "978-1234567890"


async def test_override_propagates_to_catalog(client, db_engine):
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
        await session.flush()
        catalog = CatalogEntry(
            source_run_id=run.id,
            title_en="One Piece",
            confidence=0.9,
            status="auto_confirmed",
        )
        session.add(catalog)
        await session.commit()
        pp_id = str(pp.id)

    response = await client.put(
        f"/api/v1/results/{pp_id}/override",
        json={"title_en": "One Piece Edited"},
    )
    assert response.status_code == 200

    async with factory() as session:
        from sqlalchemy import select

        stmt = select(CatalogEntry).where(CatalogEntry.source_run_id == run.id)
        cat = (await session.execute(stmt)).scalar_one()
        assert cat.title_en == "One Piece Edited"
        assert cat.status == "needs_review"


async def test_override_not_found(client):
    random_id = str(uuid.uuid4())
    response = await client.put(
        f"/api/v1/results/{random_id}/override",
        json={"title_en": "X"},
    )
    assert response.status_code == 404
