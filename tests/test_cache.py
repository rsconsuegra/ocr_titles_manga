"""Tests for the image cache service."""

import io
from datetime import UTC, datetime, timedelta

from PIL import Image

from ocr_manga_title.api.schemas.ocr import OCRResultData
from ocr_manga_title.services.cache import (
    evict_expired,
    get_ocr_result,
    get_preprocessed,
    hash_bytes,
    hash_config,
    put_ocr_result,
    put_preprocessed,
)


def _make_png_bytes(width: int = 10, height: int = 10) -> bytes:
    img = Image.new("RGB", (width, height), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_hash_bytes_deterministic():
    data = b"hello world"
    assert hash_bytes(data) == hash_bytes(data)


def test_hash_bytes_different_inputs():
    assert hash_bytes(b"aaa") != hash_bytes(b"bbb")


def test_hash_config_deterministic():
    config = {"a": 1, "b": [2, 3]}
    assert hash_config(config) == hash_config(config)


def test_hash_config_order_independent():
    assert hash_config({"a": 1, "b": 2}) == hash_config({"b": 2, "a": 1})


def test_hash_config_different_values():
    assert hash_config({"a": 1}) != hash_config({"a": 2})


async def test_put_and_get_preprocessed(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("ocr_manga_title.services.cache.CACHE_DIR", str(tmp_path / "cache"))

    raw = _make_png_bytes()
    img_hash = hash_bytes(raw)
    cfg_hash = hash_config({"grayscale": {"enabled": True}})

    from ocr_manga_title.services.image import save_bytes
    source = save_bytes(raw)

    cached = await put_preprocessed(db_session, img_hash, cfg_hash, source)
    await db_session.commit()

    result = await get_preprocessed(db_session, img_hash, cfg_hash)
    assert result is not None
    assert result == cached

    import os
    os.unlink(source)


async def test_get_preprocessed_miss(db_session):
    result = await get_preprocessed(db_session, "nonexistent", "nonexistent")
    assert result is None


async def test_put_and_get_ocr_result(db_session):
    img_hash = hash_bytes(b"test_image")
    cfg_hash = hash_config({"model": "tesseract"})
    ocr_data = OCRResultData(
        raw_text="Naruto",
        model_name="tesseract",
        confidence=0.88,
        processing_time_ms=200,
    )

    await put_ocr_result(db_session, img_hash, cfg_hash, ocr_data)
    await db_session.commit()

    result = await get_ocr_result(db_session, img_hash, cfg_hash)
    assert result is not None
    assert result.raw_text == "Naruto"
    assert result.model_name == "tesseract"
    assert result.confidence == 0.88


async def test_get_ocr_result_miss(db_session):
    result = await get_ocr_result(db_session, "nonexistent", "nonexistent")
    assert result is None


async def test_put_ocr_result_upsert(db_session):
    img_hash = hash_bytes(b"test_image")
    cfg_hash = hash_config({"model": "tesseract"})

    first = OCRResultData(raw_text="First", model_name="tesseract", confidence=0.5)
    await put_ocr_result(db_session, img_hash, cfg_hash, first)
    await db_session.commit()

    second = OCRResultData(raw_text="Second", model_name="tesseract", confidence=0.9)
    await put_ocr_result(db_session, img_hash, cfg_hash, second)
    await db_session.commit()

    result = await get_ocr_result(db_session, img_hash, cfg_hash)
    assert result.raw_text == "Second"


async def test_evict_expired(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("ocr_manga_title.services.cache.CACHE_DIR", str(tmp_path / "cache"))

    img_hash = hash_bytes(b"test_image")
    cfg_hash = hash_config({"model": "tesseract"})

    ocr_data = OCRResultData(raw_text="Expired", model_name="tesseract", confidence=0.5)
    await put_ocr_result(db_session, img_hash, cfg_hash, ocr_data)

    from ocr_manga_title.db.models import ImageCache
    from sqlalchemy import update
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
    stmt = update(ImageCache).where(ImageCache.image_hash == img_hash).values(expires_at=past)
    await db_session.execute(stmt)
    await db_session.commit()

    deleted = await evict_expired(db_session)
    await db_session.commit()
    assert deleted == 1

    result = await get_ocr_result(db_session, img_hash, cfg_hash)
    assert result is None


async def test_evict_keeps_valid(db_session):
    img_hash = hash_bytes(b"test_image")
    cfg_hash = hash_config({"model": "tesseract"})
    ocr_data = OCRResultData(raw_text="Valid", model_name="tesseract", confidence=0.9)

    await put_ocr_result(db_session, img_hash, cfg_hash, ocr_data)
    await db_session.commit()

    deleted = await evict_expired(db_session)
    await db_session.commit()
    assert deleted == 0

    result = await get_ocr_result(db_session, img_hash, cfg_hash)
    assert result is not None
    assert result.raw_text == "Valid"
