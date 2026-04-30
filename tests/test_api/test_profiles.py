import uuid

from ocr_manga_title.db.crud import create_profile


async def _seed_profile(db_engine, **overrides):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    defaults = {
        "name": "Test Profile",
        "description": "A test profile",
        "preprocess_steps": {
            "grayscale": {"enabled": True},
            "denoise": {"enabled": False, "method": "gaussian"},
        },
        "ocr_models": {
            "tesseract": {"enabled": True, "languages": ["eng", "jpn"]},
        },
        "enable_llm": True,
        "llm_provider": "openrouter",
        "llm_config": {"temperature": 0.1},
    }
    defaults.update(overrides)
    async with factory() as session:
        profile = await create_profile(session, **defaults)
        await session.commit()
        return profile


def _export_payload(**profile_overrides):
    profile = {
        "name": "Imported Profile",
        "description": "From export file",
        "preprocess_steps": {"grayscale": {"enabled": True}},
        "ocr_models": {"tesseract": {"enabled": True}},
        "enable_llm": False,
        "llm_provider": "openrouter",
    }
    profile.update(profile_overrides)
    return {
        "version": 1,
        "exported_at": "2026-01-01T00:00:00",
        "profile": profile,
    }


async def test_list_profiles_empty(client):
    response = await client.get("/api/v1/profiles")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_create_and_get_profile(client, db_engine):
    created = await _seed_profile(db_engine)
    response = await client.get(f"/api/v1/profiles/{created.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Profile"
    assert data["enable_llm"] is True


async def test_delete_profile(client, db_engine):
    created = await _seed_profile(db_engine)
    response = await client.delete(f"/api/v1/profiles/{created.id}")
    assert response.status_code == 204


async def test_export_profile(client, db_engine):
    created = await _seed_profile(db_engine)
    response = await client.get(f"/api/v1/profiles/{created.id}/export")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 1
    assert "exported_at" in data
    assert data["profile"]["name"] == "Test Profile"
    assert "Content-Disposition" in response.headers
    assert "profile.json" in response.headers["Content-Disposition"]


async def test_export_profile_not_found(client):
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/profiles/{fake_id}/export")
    assert response.status_code == 404


async def test_validate_valid_profile(client):
    payload = _export_payload()
    response = await client.post("/api/v1/profiles/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["errors"] == []
    assert data["profile"] is None


async def test_validate_invalid_step_name(client):
    payload = _export_payload(
        preprocess_steps={"nonexistent_step": {"enabled": True}},
    )
    response = await client.post("/api/v1/profiles/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["warnings"]) > 0
    assert "nonexistent_step" in data["warnings"][0]["message"]


async def test_validate_invalid_model_name(client):
    payload = _export_payload(
        ocr_models={"fake_model": {"enabled": True}},
    )
    response = await client.post("/api/v1/profiles/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["warnings"]) > 0
    assert "fake_model" in data["warnings"][0]["message"]


async def test_validate_invalid_param_range(client):
    payload = _export_payload(
        ocr_models={"tesseract": {"enabled": True, "psm": 99}},
    )
    response = await client.post("/api/v1/profiles/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["errors"]) > 0
    assert "99" in data["errors"][0]["message"]


async def test_validate_invalid_llm_provider(client):
    payload = _export_payload(llm_provider="unknown_provider")
    response = await client.post("/api/v1/profiles/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["errors"]) > 0
    assert "unknown_provider" in data["errors"][0]["message"]


async def test_validate_empty_name(client):
    payload = _export_payload(name="")
    response = await client.post("/api/v1/profiles/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["errors"]) > 0
    assert any("name" in e["field"] for e in data["errors"])


async def test_import_valid_profile(client):
    payload = _export_payload()
    response = await client.post("/api/v1/profiles/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] is not None
    assert data["profile"]["name"] == "Imported Profile"
    assert data["errors"] == []


async def test_import_invalid_profile_not_created(client):
    payload = _export_payload(name="")
    response = await client.post("/api/v1/profiles/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] is None
    assert len(data["errors"]) > 0


async def test_import_name_conflict_auto_rename(client, db_engine):
    await _seed_profile(db_engine, name="Existing Profile")

    payload = _export_payload(name="Existing Profile")
    response = await client.post("/api/v1/profiles/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] is not None
    assert data["profile"]["name"] == "Existing Profile (2)"
    assert len(data["warnings"]) > 0
    assert any("renamed" in w["message"] for w in data["warnings"])


async def test_import_preserves_preprocess_steps(client):
    payload = _export_payload(
        preprocess_steps={
            "grayscale": {"enabled": True},
            "denoise": {"enabled": True, "method": "gaussian", "strength": "light"},
        },
    )
    response = await client.post("/api/v1/profiles/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["preprocess_steps"]["denoise"]["enabled"] is True


async def test_import_with_invalid_param_returns_errors(client):
    payload = _export_payload(
        ocr_models={"tesseract": {"enabled": True, "psm": 999}},
    )
    response = await client.post("/api/v1/profiles/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] is None
    assert len(data["errors"]) > 0


async def test_import_with_unknown_step_warning(client):
    payload = _export_payload(
        preprocess_steps={
            "grayscale": {"enabled": True},
            "future_step": {"enabled": True},
        },
    )
    response = await client.post("/api/v1/profiles/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] is not None
    assert len(data["warnings"]) > 0


async def test_validate_temperature_out_of_range(client):
    payload = _export_payload(
        enable_llm=True,
        llm_config={"temperature": 5.0},
    )
    response = await client.post("/api/v1/profiles/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert any("temperature" in e["field"].lower() for e in data["errors"])
