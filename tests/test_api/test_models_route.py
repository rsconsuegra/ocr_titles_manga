from ocr_manga_title.db.models import ModelConfig


async def _seed_models(db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        configs = [
            ModelConfig(
                model_name="tesseract",
                is_enabled=True,
                language_hint="eng",
                parameters={"psm": "6", "oem": "3"},
            ),
            ModelConfig(model_name="paddle", is_enabled=False, language_hint="jpn"),
            ModelConfig(model_name="easyocr", is_enabled=False, language_hint="en"),
            ModelConfig(model_name="glm_ocr", is_enabled=False, language_hint="auto"),
        ]
        for c in configs:
            session.add(c)
        await session.commit()


async def test_list_models(client, db_engine):
    await _seed_models(db_engine)
    response = await client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4
    tess = next(m for m in data if m["model_name"] == "tesseract")
    assert tess["is_enabled"] is True
    assert tess["parameters"]["psm"] == "6"


async def test_update_model_enable(client, db_engine):
    await _seed_models(db_engine)
    response = await client.put(
        "/api/v1/models/paddle",
        json={"is_enabled": True},
    )
    assert response.status_code == 200
    assert response.json()["is_enabled"] is True


async def test_update_model_parameters(client, db_engine):
    await _seed_models(db_engine)
    response = await client.put(
        "/api/v1/models/paddle",
        json={"parameters": {"languages": ["en", "ja"]}},
    )
    assert response.status_code == 200
    assert response.json()["parameters"] == {"languages": ["en", "ja"]}


async def test_update_model_language_hint(client, db_engine):
    await _seed_models(db_engine)
    response = await client.put(
        "/api/v1/models/tesseract",
        json={"language_hint": "jpn"},
    )
    assert response.status_code == 200
    assert response.json()["language_hint"] == "jpn"


async def test_update_model_not_found(client, db_engine):
    await _seed_models(db_engine)
    response = await client.put(
        "/api/v1/models/nonexistent_model",
        json={"is_enabled": True},
    )
    assert response.status_code == 404


async def test_update_model_changes_updated_at(client, db_engine):
    await _seed_models(db_engine)
    resp1 = await client.get("/api/v1/models")
    tess_before = next(m for m in resp1.json() if m["model_name"] == "tesseract")

    import time

    time.sleep(0.01)

    resp2 = await client.put(
        "/api/v1/models/tesseract",
        json={"is_enabled": False},
    )
    assert resp2.json()["updated_at"] >= tess_before["updated_at"]
