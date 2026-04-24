import uuid

from ocr_manga_title.db.crud import create_pipeline_run
from ocr_manga_title.db.models import CatalogEntry


async def _seed_catalog(db_engine, n=3):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    entry_ids = []
    async with factory() as session:
        for i in range(n):
            run = await create_pipeline_run(
                session=session, input_image_path=f"test_{i}.png"
            )
            await session.flush()
            statuses = ["auto_confirmed", "needs_review", "rejected"]
            entry = CatalogEntry(
                source_run_id=run.id,
                title_en=f"Title {i}",
                title_ja=f"タイトル {i}" if i % 2 == 0 else None,
                code=f"978-{i:010d}" if i == 0 else None,
                confidence=0.5 + i * 0.2,
                status=statuses[i % 3],
            )
            session.add(entry)
            await session.flush()
            entry_ids.append(str(entry.id))
        await session.commit()
    return entry_ids


async def test_list_catalog_empty(client):
    response = await client.get("/api/v1/catalog")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_catalog_with_data(client, db_engine):
    await _seed_catalog(db_engine, 3)
    response = await client.get("/api/v1/catalog")
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


async def test_list_catalog_filter_by_status(client, db_engine):
    await _seed_catalog(db_engine, 3)
    response = await client.get("/api/v1/catalog?status=needs_review")
    data = response.json()
    assert all(item["status"] == "needs_review" for item in data["items"])


async def test_list_catalog_search_by_title(client, db_engine):
    await _seed_catalog(db_engine, 3)
    response = await client.get("/api/v1/catalog?search=Title+1")
    data = response.json()
    assert data["total"] >= 1
    assert any("Title 1" in (item["title_en"] or "") for item in data["items"])


async def test_list_catalog_search_by_code(client, db_engine):
    await _seed_catalog(db_engine, 3)
    response = await client.get("/api/v1/catalog?search=978")
    data = response.json()
    assert data["total"] >= 1


async def test_list_catalog_search_no_results(client, db_engine):
    await _seed_catalog(db_engine, 3)
    response = await client.get("/api/v1/catalog?search=zzznonexistent")
    data = response.json()
    assert data["total"] == 0


async def test_get_catalog_entry(client, db_engine):
    entry_ids = await _seed_catalog(db_engine, 1)
    response = await client.get(f"/api/v1/catalog/{entry_ids[0]}")
    assert response.status_code == 200
    assert response.json()["title_en"] == "Title 0"


async def test_get_catalog_entry_not_found(client):
    response = await client.get(f"/api/v1/catalog/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_update_catalog_status(client, db_engine):
    entry_ids = await _seed_catalog(db_engine, 1)
    response = await client.put(
        f"/api/v1/catalog/{entry_ids[0]}",
        json={"status": "rejected"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


async def test_update_catalog_title_and_code(client, db_engine):
    entry_ids = await _seed_catalog(db_engine, 1)
    response = await client.put(
        f"/api/v1/catalog/{entry_ids[0]}",
        json={"title_en": "New Title", "code": "ISBN-999"},
    )
    assert response.status_code == 200
    assert response.json()["title_en"] == "New Title"
    assert response.json()["code"] == "ISBN-999"


async def test_update_catalog_invalid_status(client, db_engine):
    entry_ids = await _seed_catalog(db_engine, 1)
    response = await client.put(
        f"/api/v1/catalog/{entry_ids[0]}",
        json={"status": "invalid"},
    )
    assert response.status_code == 400


async def test_update_catalog_not_found(client):
    response = await client.put(
        f"/api/v1/catalog/{uuid.uuid4()}",
        json={"title_en": "X"},
    )
    assert response.status_code == 404


async def test_export_catalog_csv(client, db_engine):
    await _seed_catalog(db_engine, 2)
    response = await client.get("/api/v1/catalog/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    lines = response.text.strip().split("\n")
    assert lines[0].startswith("id,title_en")
    assert len(lines) == 3


async def test_export_catalog_empty(client):
    response = await client.get("/api/v1/catalog/export")
    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert len(lines) == 1
