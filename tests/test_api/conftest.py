import io

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ocr_manga_title.api.app import create_app


@pytest.fixture
async def client(db_engine, monkeypatch, tmp_path):
    from ocr_manga_title.api import dependencies as deps_module
    from ocr_manga_title.api.routes import batches as batches_module
    from ocr_manga_title.api.routes import inputs as inputs_module
    from ocr_manga_title.db import session as session_module

    test_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(session_module, "async_session_factory", test_factory)
    monkeypatch.setattr(deps_module, "async_session_factory", test_factory)
    monkeypatch.setattr(inputs_module, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(batches_module, "UPLOAD_DIR", tmp_path / "uploads")

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def blank_image():
    return io.BytesIO(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
