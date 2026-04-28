"""Content-addressable image cache — avoids redundant preprocessing and OCR.

.. note::
   This module uses PostgreSQL-specific ``INSERT ... ON CONFLICT`` (via
   ``sqlalchemy.dialects.postgresql.insert``).  PostgreSQL is a hard
   requirement for the cache layer; SQLite is **not** supported.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.schemas.ocr import OCRResultData
from ocr_manga_title.services.image import decode_bytes
from ocr_manga_title.services.preprocess import run_preprocessing_pipeline_from_array
from ocr_manga_title.services.ocr import run_all_enabled_models, run_single_model
from ocr_manga_title.settings import CACHE_DIR, CACHE_TTL_DAYS

logger = logging.getLogger(__name__)


def hash_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def hash_config(config: dict) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _cache_dir() -> Path:
    p = Path(CACHE_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _expiry() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None) + timedelta(days=CACHE_TTL_DAYS)


async def get_preprocessed(
    session: AsyncSession, image_hash: str, config_hash: str
) -> str | None:
    from ocr_manga_title.db.models import ImageCache

    now = datetime.now(UTC).replace(tzinfo=None)
    stmt = (
        delete(ImageCache)
        .where(
            ImageCache.image_hash == image_hash,
            ImageCache.cache_type == "preprocess",
            ImageCache.expires_at < now,
        )
    )
    await session.execute(stmt)
    await session.flush()

    stmt = select(ImageCache).where(
        ImageCache.image_hash == image_hash,
        ImageCache.config_hash == config_hash,
        ImageCache.cache_type == "preprocess",
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    if row.result_path and Path(row.result_path).exists():
        return row.result_path
    await session.execute(delete(ImageCache).where(ImageCache.id == row.id))
    await session.flush()
    return None


async def put_preprocessed(
    session: AsyncSession,
    image_hash: str,
    config_hash: str,
    source_path: str,
) -> str:
    from ocr_manga_title.db.models import ImageCache

    cache_dir = _cache_dir()
    ext = Path(source_path).suffix or ".png"
    cached_name = f"{image_hash}_{config_hash}{ext}"
    cached_path = str(cache_dir / cached_name)
    shutil.copy2(source_path, cached_path)

    expires = _expiry()
    stmt = pg_insert(ImageCache).values(
        id=uuid.uuid4(),
        image_hash=image_hash,
        config_hash=config_hash,
        cache_type="preprocess",
        result_path=cached_path,
        result_data=None,
        expires_at=expires,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["image_hash", "config_hash", "cache_type"],
        set_={"result_path": cached_path, "expires_at": expires},
    )
    await session.execute(stmt)
    await session.flush()
    return cached_path


async def get_ocr_result(
    session: AsyncSession, image_hash: str, config_hash: str
) -> OCRResultData | None:
    from ocr_manga_title.db.models import ImageCache

    now = datetime.now(UTC).replace(tzinfo=None)
    stmt = (
        delete(ImageCache)
        .where(
            ImageCache.image_hash == image_hash,
            ImageCache.cache_type == "ocr",
            ImageCache.expires_at < now,
        )
    )
    await session.execute(stmt)
    await session.flush()

    stmt = select(ImageCache).where(
        ImageCache.image_hash == image_hash,
        ImageCache.config_hash == config_hash,
        ImageCache.cache_type == "ocr",
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None or row.result_data is None:
        return None
    return OCRResultData(**row.result_data)


async def put_ocr_result(
    session: AsyncSession,
    image_hash: str,
    config_hash: str,
    ocr_result: OCRResultData,
) -> None:
    from ocr_manga_title.db.models import ImageCache

    expires = _expiry()
    data = ocr_result.model_dump()
    stmt = pg_insert(ImageCache).values(
        id=uuid.uuid4(),
        image_hash=image_hash,
        config_hash=config_hash,
        cache_type="ocr",
        result_path=None,
        result_data=data,
        expires_at=expires,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["image_hash", "config_hash", "cache_type"],
        set_={"result_data": data, "expires_at": expires},
    )
    await session.execute(stmt)
    await session.flush()


async def evict_expired(session: AsyncSession) -> int:
    from ocr_manga_title.db.models import ImageCache

    now = datetime.now(UTC).replace(tzinfo=None)
    stmt = select(ImageCache.result_path).where(
        ImageCache.expires_at < now,
        ImageCache.result_path.isnot(None),
    )
    result = await session.execute(stmt)
    orphan_paths = [row[0] for row in result.all()]

    stmt = delete(ImageCache).where(ImageCache.expires_at < now)
    result = await session.execute(stmt)
    deleted = result.rowcount
    await session.flush()

    for path_str in orphan_paths:
        try:
            Path(path_str).unlink(missing_ok=True)
        except OSError:
            pass

    if deleted:
        logger.info("Cache eviction: removed %d expired entries", deleted)
    return deleted


async def run_preprocessing_cached(
    session: AsyncSession,
    raw: bytes,
    steps_config: dict,
) -> str:
    image_hash = hash_bytes(raw)
    config_hash = hash_config(steps_config)

    cached = await get_preprocessed(session, image_hash, config_hash)
    if cached:
        logger.info("Preprocessing cache hit: %s", image_hash[:12])
        return cached

    image_array = decode_bytes(raw)
    result_path = await asyncio.to_thread(
        run_preprocessing_pipeline_from_array, image_array, steps_config
    )

    cached_path = await put_preprocessed(session, image_hash, config_hash, result_path)
    logger.info("Preprocessing cache miss: %s (cached)", image_hash[:12])
    return cached_path


async def run_ocr_cached(
    session: AsyncSession,
    image_hash: str,
    model_name: str,
    image_path: str,
    params: dict | None = None,
) -> OCRResultData:
    params = params or {}
    config_hash = hash_config({"model": model_name, **params})

    cached = await get_ocr_result(session, image_hash, config_hash)
    if cached:
        logger.info("OCR cache hit: %s/%s", image_hash[:12], model_name)
        return cached

    result = await asyncio.to_thread(run_single_model, model_name, image_path, params)

    if not result.error:
        await put_ocr_result(session, image_hash, config_hash, result)
        logger.info("OCR cache miss: %s/%s (cached)", image_hash[:12], model_name)
    else:
        logger.info("OCR cache miss: %s/%s (error, not cached)", image_hash[:12], model_name)

    return result


async def run_all_models_cached(
    session: AsyncSession,
    image_hash: str,
    image_path: str,
    ocr_config: dict,
) -> list[OCRResultData]:
    from ocr_manga_title.engine.registry import MODEL_REGISTRY

    results: list[OCRResultData] = []
    uncached_models: list[tuple[str, dict]] = []

    for name, descriptor in MODEL_REGISTRY.items():
        override = ocr_config.get(name, {})
        if not override.get("enabled", False):
            continue

        params = {k: v for k, v in override.items() if k != "enabled"}
        config_hash = hash_config({"model": name, **params})

        cached = await get_ocr_result(session, image_hash, config_hash)
        if cached:
            logger.info("OCR cache hit: %s/%s", image_hash[:12], name)
            results.append(cached)
        else:
            uncached_models.append((name, override))

    if uncached_models:
        ocr_results = run_all_enabled_models(image_path, ocr_config)

        for ocr_result in ocr_results:
            if not ocr_result.error:
                override = dict(ocr_config.get(ocr_result.model_name, {}))
                params = {k: v for k, v in override.items() if k != "enabled"}
                config_hash = hash_config(
                    {"model": ocr_result.model_name, **params}
                )
                await put_ocr_result(session, image_hash, config_hash, ocr_result)
            results.append(ocr_result)

    return results
