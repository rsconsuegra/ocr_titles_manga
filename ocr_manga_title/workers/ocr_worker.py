import asyncio
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

import dramatiq
from sqlalchemy import select

import ocr_manga_title.workers.broker  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ocr_manga_title.config import load_config, load_preprocess_config
from ocr_manga_title.db.crud import list_model_configs, update_batch_progress
from ocr_manga_title.db.enums import RunStatus
from ocr_manga_title.db.models import PipelineRun
from ocr_manga_title.engine import OCREngine
from ocr_manga_title.exceptions import PermanentError
from ocr_manga_title.schemas import ModelConfig as ModelConfigSchema
from ocr_manga_title.services.cache import hash_bytes, hash_config, put_ocr_result
from ocr_manga_title.services.ocr import build_model_config
from ocr_manga_title.services.pipeline import save_pipeline_results
from ocr_manga_title.settings import (
    CONFIG_PATH,
    DATABASE_URL,
    DB_WORKER_MAX_OVERFLOW,
    DB_WORKER_POOL_SIZE,
    PREPROCESS_CONFIG_PATH,
)

logger = logging.getLogger(__name__)

MIN_MEMORY_MB = 512


def _check_available_memory() -> int:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except (FileNotFoundError, ValueError, IndexError):
        return -1
    return -1


def _require_memory(context: str) -> None:
    available = _check_available_memory()
    if available >= 0 and available < MIN_MEMORY_MB:
        raise PermanentError(
            f"Insufficient memory to {context}: "
            f"{available}MB available, {MIN_MEMORY_MB}MB required. "
            f"Increase Docker/Colima memory allocation."
        )


class RunCancelled(Exception):
    pass


async def _check_cancelled(session: AsyncSession, run_id: uuid.UUID) -> None:
    stmt = select(PipelineRun).where(PipelineRun.id == run_id)
    result = await session.execute(stmt)
    run = result.scalar_one_or_none()
    if run and run.status == RunStatus.CANCELLED:
        raise RunCancelled(f"Run {run_id} was cancelled")


def _run_async(coro):
    loop = asyncio.new_event_loop()
    database_url = DATABASE_URL
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=DB_WORKER_POOL_SIZE,
        max_overflow=DB_WORKER_MAX_OVERFLOW,
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    try:
        return loop.run_until_complete(coro(session_factory))
    finally:
        loop.run_until_complete(engine.dispose())
        loop.close()


async def _get_model_configs(session: AsyncSession) -> dict[str, ModelConfigSchema]:
    rows = await list_model_configs(session, enabled_only=True)
    configs = {}
    for row in rows:
        configs[row.model_name] = ModelConfigSchema(
            name=row.model_name,
            enabled=row.is_enabled,
            language=row.language_hint or "",
            parameters=row.parameters or {},
        )
    return configs


def _build_model_configs_from_snapshot(
    ocr_models: dict,
) -> dict[str, ModelConfigSchema]:
    configs: dict[str, ModelConfigSchema] = {}
    for model_name, override in ocr_models.items():
        if not override.get("enabled", False):
            continue
        result = build_model_config(model_name, override)
        if result is not None:
            configs[model_name] = result[0]
    return configs


def _build_preprocess_raw(preprocess_steps: dict) -> dict:
    if not preprocess_steps:
        return {"preprocessing": {"enabled": False}}
    return {"preprocessing": {"enabled": True, "steps": preprocess_steps}}


async def _mark_run_failed(run_id: str, error_message: str) -> None:
    engine = create_async_engine(
        DATABASE_URL, echo=False,
        pool_size=DB_WORKER_POOL_SIZE, max_overflow=DB_WORKER_MAX_OVERFLOW,
    )
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with sf() as session:
            try:
                run_uuid = uuid.UUID(run_id)
            except ValueError:
                return
            stmt = select(PipelineRun).where(PipelineRun.id == run_uuid)
            result = await session.execute(stmt)
            run = result.scalar_one_or_none()
            if not run or run.status in (RunStatus.COMPLETED, RunStatus.FAILED):
                return
            run.status = RunStatus.FAILED
            run.error_message = error_message[:1000]
            run.completed_at = datetime.now(UTC).replace(tzinfo=None)
            await session.commit()
            if run.batch_run_id:
                await update_batch_progress(session, run.batch_run_id)
                await session.commit()
    finally:
        await engine.dispose()


@dramatiq.actor(
    max_retries=3,
    min_backoff=10000,
    max_backoff=60000,
    time_limit=900000,
)
def process_pipeline_run(run_id: str):
    try:
        _run_async(lambda sf: _process(run_id, sf))
    except Exception as e:
        logger.error("Worker-level error for run %s: %s", run_id, e)
        try:
            asyncio.run(_mark_run_failed(run_id, str(e)))
        except Exception:
            logger.exception("Failed to mark run %s as failed", run_id)
        raise


async def _process(run_id: str, session_factory: async_sessionmaker):
    async with session_factory() as session:
        try:
            run_uuid = uuid.UUID(run_id)
        except ValueError:
            logger.error("Invalid run_id: %s", run_id)
            return

        stmt = select(PipelineRun).where(PipelineRun.id == run_uuid)
        result = await session.execute(stmt)
        run = result.scalar_one_or_none()
        if not run:
            logger.error("Pipeline run not found: %s", run_id)
            return

        await _check_cancelled(session, run_uuid)
        run.status = RunStatus.PROCESSING
        await session.commit()

        try:
            image_path = Path(run.input_image_path)
            if not image_path.exists():
                raise PermanentError(f"Image not found: {run.input_image_path}")

            app_config = load_config(CONFIG_PATH)

            if run.preprocess_config:
                snapshot = run.preprocess_config
                ocr_models_snapshot = snapshot.get("ocr_models", {})
                model_configs = _build_model_configs_from_snapshot(
                    ocr_models_snapshot
                )
                preprocess_raw = _build_preprocess_raw(
                    snapshot.get("preprocess_steps", {})
                )
                enable_llm = snapshot.get("enable_llm", True)
            else:
                ocr_models_snapshot = {}
                model_configs = await _get_model_configs(session)
                preprocess_raw = load_preprocess_config(PREPROCESS_CONFIG_PATH)
                enable_llm = True

            _require_memory("load OCR models")

            engine = OCREngine(
                config=app_config,
                ocr_config=model_configs,
                preprocess_config=preprocess_raw,
            )

            await _check_cancelled(session, run_uuid)

            pipeline_result = engine.process(run.input_image_path, enable_llm=enable_llm)

            try:
                image_hash = hash_bytes(image_path.read_bytes())
                for ocr_res in pipeline_result.ocr_results:
                    if ocr_res.error:
                        continue
                    override = dict(ocr_models_snapshot.get(ocr_res.model_name, {}))
                    params = {k: v for k, v in override.items() if k != "enabled"}
                    config_hash = hash_config({"model": ocr_res.model_name, **params})
                    from ocr_manga_title.api.schemas.ocr import OCRResultData
                    await put_ocr_result(
                        session,
                        image_hash,
                        config_hash,
                        OCRResultData(
                            raw_text=ocr_res.raw_text,
                            model_name=ocr_res.model_name,
                            confidence=ocr_res.confidence,
                            processing_time_ms=ocr_res.processing_time_ms,
                            error=ocr_res.error,
                        ),
                    )
            except Exception as cache_err:
                logger.warning("Failed to cache OCR results: %s", cache_err)

            await save_pipeline_results(session, run.id, pipeline_result)

            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.now(UTC).replace(tzinfo=None)
            await session.commit()

            if run.batch_run_id:
                await update_batch_progress(session, run.batch_run_id)
                await session.commit()

            logger.info("Pipeline run %s completed successfully", run_id)

        except RunCancelled:
            run.status = RunStatus.CANCELLED
            run.completed_at = datetime.now(UTC).replace(tzinfo=None)
            await session.commit()

            if run.batch_run_id:
                await update_batch_progress(session, run.batch_run_id)
                await session.commit()

            logger.info("Pipeline run %s cancelled", run_id)

        except PermanentError as e:
            run.status = RunStatus.FAILED
            run.error_message = str(e)[:1000]
            run.completed_at = datetime.now(UTC).replace(tzinfo=None)
            await session.commit()

            if run.batch_run_id:
                await update_batch_progress(session, run.batch_run_id)
                await session.commit()

            logger.error("Pipeline run %s failed permanently: %s", run_id, e)

        except Exception as e:
            run.status = RunStatus.FAILED
            run.error_message = str(e)[:1000]
            run.completed_at = datetime.now(UTC).replace(tzinfo=None)
            await session.commit()

            if run.batch_run_id:
                await update_batch_progress(session, run.batch_run_id)
                await session.commit()

            logger.error("Pipeline run %s failed (will retry): %s", run_id, e)
            raise
