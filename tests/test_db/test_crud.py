from ocr_manga_title.db.crud import (
    get_active_prompt,
    get_model_config,
    list_model_configs,
    list_prompts,
    update_model_config,
)
from ocr_manga_title.db.models import ModelConfig, PromptVersion


async def test_get_active_prompt_returns_active(db_session):
    pv = PromptVersion(
        prompt_type="llm",
        content="Extract the title",
        version_number=1,
        is_active=True,
    )
    db_session.add(pv)
    await db_session.flush()

    result = await get_active_prompt(db_session, "llm")
    assert result is not None
    assert result.content == "Extract the title"
    assert result.version_number == 1


async def test_get_active_prompt_returns_none_for_type(db_session):
    result = await get_active_prompt(db_session, "ocr")
    assert result is None


async def test_get_active_prompt_prefers_higher_version(db_session):
    v1 = PromptVersion(
        prompt_type="llm", content="v1 prompt", version_number=1, is_active=True
    )
    v2 = PromptVersion(
        prompt_type="llm", content="v2 prompt", version_number=2, is_active=True
    )
    db_session.add_all([v1, v2])
    await db_session.flush()

    result = await get_active_prompt(db_session, "llm")
    assert result.version_number == 2
    assert result.content == "v2 prompt"


async def test_get_active_prompt_ignores_inactive(db_session):
    v1 = PromptVersion(
        prompt_type="llm", content="v1", version_number=1, is_active=False
    )
    v2 = PromptVersion(
        prompt_type="llm", content="v2", version_number=2, is_active=True
    )
    db_session.add_all([v1, v2])
    await db_session.flush()

    result = await get_active_prompt(db_session, "llm")
    assert result.version_number == 2


async def test_list_prompts_returns_all(db_session):
    p1 = PromptVersion(prompt_type="llm", content="p1", version_number=1)
    p2 = PromptVersion(prompt_type="ocr", content="p2", version_number=1)
    db_session.add_all([p1, p2])
    await db_session.flush()

    result = await list_prompts(db_session)
    assert len(result) == 2


async def test_list_prompts_filters_by_type(db_session):
    p1 = PromptVersion(prompt_type="llm", content="p1", version_number=1)
    p2 = PromptVersion(prompt_type="ocr", content="p2", version_number=1)
    db_session.add_all([p1, p2])
    await db_session.flush()

    result = await list_prompts(db_session, prompt_type="llm")
    assert len(result) == 1
    assert result[0].prompt_type == "llm"


async def test_get_model_config_found(db_session):
    mc = ModelConfig(model_name="tesseract", is_enabled=True)
    db_session.add(mc)
    await db_session.flush()

    result = await get_model_config(db_session, "tesseract")
    assert result is not None
    assert result.model_name == "tesseract"


async def test_get_model_config_not_found(db_session):
    result = await get_model_config(db_session, "nonexistent")
    assert result is None


async def test_list_model_configs(db_session):
    for name in ["tesseract", "paddle", "easyocr"]:
        db_session.add(ModelConfig(model_name=name, is_enabled=True))
    db_session.add(ModelConfig(model_name="glm_ocr", is_enabled=False))
    await db_session.flush()

    all_configs = await list_model_configs(db_session)
    assert len(all_configs) == 4

    enabled = await list_model_configs(db_session, enabled_only=True)
    assert len(enabled) == 3
    assert all(c.is_enabled for c in enabled)


async def test_update_model_config(db_session):
    mc = ModelConfig(model_name="tesseract", is_enabled=True, language_hint="eng")
    db_session.add(mc)
    await db_session.flush()

    updated = await update_model_config(
        db_session, "tesseract", is_enabled=False, language_hint="eng+jpn"
    )
    assert updated is not None
    assert updated.is_enabled is False
    assert updated.language_hint == "eng+jpn"


async def test_update_model_config_not_found(db_session):
    result = await update_model_config(db_session, "nonexistent", is_enabled=False)
    assert result is None
