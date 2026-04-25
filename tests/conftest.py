import io

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ocr_manga_title.db.models import Base


@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
def valid_configs_toml(tmp_path):
    toml_content = '''
[openrouter]
api_key = "sk-or-test-key-12345"
default_model = "google/gemini-2.5-flash"
base_url = "https://openrouter.ai/api/v1"
'''
    config_file = tmp_path / "configs.toml"
    config_file.write_text(toml_content)
    return config_file


@pytest.fixture
def valid_ocrs_yaml(tmp_path):
    yaml_content = """
models:
  tesseract:
    enabled: true
    languages: ["eng", "jpn"]
    psm: 3
    oem: 3
  paddle:
    enabled: false
    languages: ["en", "ja"]
  easyocr:
    enabled: false
    languages: ["en", "ja"]
  glm_ocr:
    enabled: false
    api_endpoint: ""
"""
    yaml_file = tmp_path / "ocrs.yaml"
    yaml_file.write_text(yaml_content)
    return yaml_file


@pytest.fixture
def blank_image(tmp_path):
    img = Image.new("RGB", (1, 1), "white")
    path = tmp_path / "blank.png"
    img.save(path)
    return str(path)


@pytest.fixture
def blank_image_bytes():
    return io.BytesIO(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture
def sample_text_with_isbn():
    return "One Piece ワンピース ISBN 978-0-306-40615-7"


@pytest.fixture
def sample_ocr_result():
    from ocr_manga_title.schemas import OCRResult

    return OCRResult(
        raw_text="ワンピース One Piece ISBN 978-0-306-40615-7",
        model_name="manga-ocr",
        confidence=0.7,
        processing_time_ms=150,
    )
