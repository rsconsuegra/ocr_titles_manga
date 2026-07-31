"""Content-addressable image cache — avoids redundant preprocessing and OCR.

.. note::
   This module uses PostgreSQL-specific ``INSERT ... ON CONFLICT`` (via
   ``sqlalchemy.dialects.postgresql.insert``).  PostgreSQL is a hard
   requirement for the cache layer; SQLite is **not** supported.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.schemas.ocr import OCRResultData
from ocr_manga_title.schemas import utcnow
from ocr_manga_title.services.image import decode_bytes
from ocr_manga_title.services.ocr import run_all_enabled_models, run_single_model
from ocr_manga_title.services.preprocess import run_preprocessing_pipeline_from_array
from ocr_manga_title.settings import CACHE_DIR, CACHE_TTL_DAYS

logger = logging.getLogger(__name__)

_HASH_DISPLAY_LEN = 12


@dataclass(frozen=True)
class CacheEntry:
    """Bundle of fields for a single cache upsert operation."""

    image_hash: str
    config_hash: str
    cache_type: str
    result_path: str | None
    result_data: object
    expires_at: datetime


def hash_bytes(raw: bytes) -> str:
    """Return the SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(raw).hexdigest()


def hash_config(config: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 hex digest of a config dict."""
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _cache_dir() -> Path:
    p = Path(CACHE_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _expiry() -> datetime:
    return utcnow() + timedelta(days=CACHE_TTL_DAYS)


async def _evict_expired(
    session: AsyncSession, image_hash: str, cache_type: str
) -> None:
    from ocr_manga_title.db.models import ImageCache

    now = utcnow()
    stmt = delete(ImageCache).where(
        ImageCache.image_hash == image_hash,
        ImageCache.cache_type == cache_type,
        ImageCache.expires_at < now,
    )
    await session.execute(stmt)
    await session.flush()


async def _upsert_cache_entry(
    session: AsyncSession,
    entry: CacheEntry,
) -> None:
    from ocr_manga_title.db.models import ImageCache

    stmt = pg_insert(ImageCache).values(
        id=uuid.uuid4(),
        image_hash=entry.image_hash,
        config_hash=entry.config_hash,
        cache_type=entry.cache_type,
        result_path=entry.result_path,
        result_data=entry.result_data,
        expires_at=entry.expires_at,
    )
    set_ = {"result_data": entry.result_data, "expires_at": entry.expires_at}
    if entry.result_path is not None:
        set_["result_path"] = entry.result_path
    stmt = stmt.on_conflict_do_update(
        index_elements=["image_hash", "config_hash", "cache_type"],
        set_=set_,
    )
    await session.execute(stmt)
    await session.flush()


async def get_preprocessed(
    session: AsyncSession,
    image_hash: str,
    config_hash: str,
) -> tuple[str, Any] | None:
    """Look up a cached preprocessed image by content and config hash."""
    from ocr_manga_title.db.models import ImageCache

    await _evict_expired(session, image_hash, "preprocess")

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
        return (row.result_path, row.result_data)
    await session.execute(delete(ImageCache).where(ImageCache.id == row.id))
    await session.flush()
    return None


async def put_preprocessed(
    session: AsyncSession,
    image_hash: str,
    config_hash: str,
    source_path: str,
    step_metadata: list[tuple[str, dict[str, Any]]] | None = None,
) -> tuple[str, list[tuple[str, dict[str, Any]]] | None]:
    """Store a preprocessed image in the file cache and record the entry."""
    cache_dir = _cache_dir()
    ext = Path(source_path).suffix or ".png"
    cached_name = f"{image_hash}_{config_hash}{ext}"
    cached_path = str(cache_dir / cached_name)
    shutil.copy2(source_path, cached_path)

    await _upsert_cache_entry(
        session,
        CacheEntry(
            image_hash=image_hash,
            config_hash=config_hash,
            cache_type="preprocess",
            result_path=cached_path,
            result_data=step_metadata,
            expires_at=_expiry(),
        ),
    )
    return cached_path, step_metadata


async def get_ocr_result(
    session: AsyncSession, image_hash: str, config_hash: str
) -> OCRResultData | None:
    """Look up a cached OCR result by content and config hash."""
    from ocr_manga_title.db.models import ImageCache

    await _evict_expired(session, image_hash, "ocr")

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
    """Persist an OCR result into the database cache."""
    await _upsert_cache_entry(
        session,
        CacheEntry(
            image_hash=image_hash,
            config_hash=config_hash,
            cache_type="ocr",
            result_path=None,
            result_data=ocr_result.model_dump(),
            expires_at=_expiry(),
        ),
    )


async def evict_expired(session: AsyncSession) -> int:
    """Remove all expired cache entries and their associated files."""
    from ocr_manga_title.db.models import ImageCache

    now = utcnow()
    stmt = select(ImageCache.result_path).where(
        ImageCache.expires_at < now,
        ImageCache.result_path.isnot(None),
    )
    result = await session.execute(stmt)
    orphan_paths = [row[0] for row in result.all()]

    del_stmt = delete(ImageCache).where(ImageCache.expires_at < now)
    del_result = await session.execute(del_stmt)
    deleted: int = del_result.rowcount  # type: ignore[attr-defined]
    await session.flush()

    for path_str in orphan_paths:
        with contextlib.suppress(OSError):
            Path(path_str).unlink(missing_ok=True)

    if deleted:
        logger.info("Cache eviction: removed %d expired entries", deleted)
    return deleted


def _model_config_hash(model_name: str, override: dict[str, Any]) -> str:
    params = {k: v for k, v in override.items() if k != "enabled"}
    return hash_config({"model": model_name, **params})


async def run_preprocessing_cached(
    session: AsyncSession,
    raw: bytes,
    steps_config: dict[str, Any],
) -> tuple[str, list[tuple[str, dict[str, Any]]] | None]:
    """Run preprocessing with transparent content-addressable caching."""
    image_hash = hash_bytes(raw)
    config_hash = hash_config(steps_config)

    cached = await get_preprocessed(session, image_hash, config_hash)
    if cached:
        logger.info("Preprocessing cache hit: %s", image_hash[:_HASH_DISPLAY_LEN])
        return cached

    image_array = decode_bytes(raw)
    result_path, step_metadata = await asyncio.to_thread(
        run_preprocessing_pipeline_from_array, image_array, steps_config
    )

    cached_result = await put_preprocessed(
        session,
        image_hash,
        config_hash,
        result_path,
        step_metadata,
    )
    logger.info("Preprocessing cache miss: %s (cached)", image_hash[:_HASH_DISPLAY_LEN])
    return cached_result


async def run_ocr_cached(
    session: AsyncSession,
    image_hash: str,
    model_name: str,
    image_path: str,
    params: dict[str, Any] | None = None,
) -> OCRResultData:
    """Run a single OCR model with transparent caching."""
    params = params or {}
    config_hash = hash_config({"model": model_name, **params})

    cached = await get_ocr_result(session, image_hash, config_hash)
    if cached:
        logger.info("OCR cache hit: %s/%s", image_hash[:_HASH_DISPLAY_LEN], model_name)
        return cached

    result = await asyncio.to_thread(run_single_model, model_name, image_path, params)

    if not result.error:
        await put_ocr_result(session, image_hash, config_hash, result)
        logger.info(
            "OCR cache miss: %s/%s (cached)", image_hash[:_HASH_DISPLAY_LEN], model_name
        )
    else:
        logger.info(
            "OCR cache miss: %s/%s (error, not cached)",
            image_hash[:_HASH_DISPLAY_LEN],
            model_name,
        )

    return result


async def run_all_models_cached(
    session: AsyncSession,
    image_hash: str,
    image_path: str,
    ocr_config: dict[str, Any],
) -> list[OCRResultData]:
    """Run all enabled OCR models with transparent caching."""
    from ocr_manga_title.engine.registry import MODEL_REGISTRY

    results: list[OCRResultData] = []
    uncached_models: list[tuple[str, dict[str, Any]]] = []

    for name, _descriptor in MODEL_REGISTRY.items():
        override = ocr_config.get(name, {})
        if not override.get("enabled", False):
            continue

        config_hash = _model_config_hash(name, override)

        cached = await get_ocr_result(session, image_hash, config_hash)
        if cached:
            logger.info("OCR cache hit: %s/%s", image_hash[:_HASH_DISPLAY_LEN], name)
            results.append(cached)
        else:
            uncached_models.append((name, override))

    if uncached_models:
        uncached_config = dict(uncached_models)
        ocr_results = await asyncio.to_thread(
            run_all_enabled_models, image_path, uncached_config
        )

        for ocr_result in ocr_results:
            if not ocr_result.error:
                override = dict(uncached_config.get(ocr_result.model_name, {}))
                config_hash = _model_config_hash(ocr_result.model_name, override)
                await put_ocr_result(session, image_hash, config_hash, ocr_result)
            results.append(ocr_result)

    return results
