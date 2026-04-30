import asyncio
import logging
import threading
import uuid
from pathlib import Path

import dramatiq
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import ocr_manga_title.workers.broker  # noqa: F401
from ocr_manga_title.config import (
    load_config,
    load_preprocess_config,
    resolve_model_configs,
)
from ocr_manga_title.db.crud import list_model_configs, update_batch_progress
from ocr_manga_title.db.enums import RunStatus
from ocr_manga_title.db.models import PipelineRun
from ocr_manga_title.engine import OCREngine
from ocr_manga_title.schemas import utcnow
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

if logging.getLogger().handlers:
    from ocr_manga_title.services.warmup import warmup_models
    warmup_models()

MIN_MEMORY_MB = 512
_MAX_ERROR_LENGTH = 1000

_worker_engine = None
_worker_session_factory = None


def _get_worker_session_factory() -> async_sessionmaker:
    global _worker_engine, _worker_session_factory
    if _worker_session_factory is None:
        _worker_engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=DB_WORKER_POOL_SIZE,
            max_overflow=DB_WORKER_MAX_OVERFLOW,
        )
        _worker_session_factory = async_sessionmaker(
            _worker_engine, class_=AsyncSession, expire_on_commit=False
        )
    return _worker_session_factory


def _check_available_memory() -> int:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except (FileNotFoundError, ValueError, IndexError):
        logger.debug("/proc/meminfo unavailable — memory guard disabled")
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


_loop_local = threading.local()


def _get_event_loop() -> asyncio.AbstractEventLoop:
    loop = getattr(_loop_local, "loop", None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        _loop_local.loop = loop
    return loop


def _run_async(coro):
    sf = _get_worker_session_factory()
    return _get_event_loop().run_until_complete(coro(sf))


async def _get_model_configs(session: AsyncSession) -> dict[str, ModelConfigSchema]:
    rows = await list_model_configs(session, enabled_only=False)
    db_overrides = {
        row.model_name: {"is_enabled": row.is_enabled, "parameters": row.parameters or {}}
        for row in rows
    }
    resolved = resolve_model_configs(db_overrides)

    configs = {}
    for name, cfg in resolved.items():
        if not cfg.enabled:
            continue
        configs[name] = ModelConfigSchema(
            name=name,
            enabled=True,
            language="",
            parameters=cfg.parameters,
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


async def _resolve_run_config(
    session: AsyncSession, run: PipelineRun
) -> tuple:
    app_config = load_config(CONFIG_PATH)
    if run.preprocess_config:
        snapshot = run.preprocess_config
        ocr_models_snapshot = snapshot.get("ocr_models", {})
        model_configs = _build_model_configs_from_snapshot(ocr_models_snapshot)
        preprocess_raw = _build_preprocess_raw(snapshot.get("preprocess_steps", {}))
        enable_llm = snapshot.get("enable_llm", True)
        llm_prov = snapshot.get("llm_provider", "openrouter")
        llm_cfg = snapshot.get("llm_config")
    else:
        ocr_models_snapshot = {}
        model_configs = await _get_model_configs(session)
        preprocess_raw = load_preprocess_config(PREPROCESS_CONFIG_PATH)
        enable_llm = True
        llm_prov = "openrouter"
        llm_cfg = None

    app_config.llm_provider = llm_prov
    return app_config, model_configs, preprocess_raw, enable_llm, llm_prov, llm_cfg, ocr_models_snapshot


async def _cache_ocr_results(
    session: AsyncSession,
    ocr_results,
    ocr_models_snapshot: dict,
    image_hash: str,
) -> None:
    try:
        from ocr_manga_title.api.schemas.ocr import OCRResultData

        for ocr_res in ocr_results:
            if ocr_res.error:
                continue
            override = dict(ocr_models_snapshot.get(ocr_res.model_name, {}))
            params = {k: v for k, v in override.items() if k != "enabled"}
            config_hash = hash_config({"model": ocr_res.model_name, **params})
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
                    blocks=[
                        {"bbox": b.bbox, "text": b.text, "confidence": b.confidence}
                        for b in ocr_res.blocks
                    ] if ocr_res.blocks else None,
                ),
            )
    except Exception as cache_err:
        logger.warning("Failed to cache OCR results: %s", cache_err)


async def _mark_run_failed(run_id: str, error_message: str) -> None:
    sf = _get_worker_session_factory()
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
        run.error_message = error_message[:_MAX_ERROR_LENGTH]
        run.completed_at = utcnow()
        if run.batch_run_id:
            await update_batch_progress(session, run.batch_run_id)
        await session.commit()


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
            _get_event_loop().run_until_complete(_mark_run_failed(run_id, str(e)))
        except Exception:
            logger.exception("Failed to mark run %s as failed", run_id)
        raise


async def _finalize_run(
    session: AsyncSession,
    run: PipelineRun,
    status_val: RunStatus,
    error_message: str | None = None,
) -> None:
    run.status = status_val
    if error_message is not None:
        run.error_message = error_message[:_MAX_ERROR_LENGTH]
    run.completed_at = utcnow()
    if run.batch_run_id:
        await update_batch_progress(session, run.batch_run_id)
    await session.commit()


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

            (app_config, model_configs, preprocess_raw,
             enable_llm, llm_prov, llm_cfg,
             ocr_models_snapshot) = await _resolve_run_config(session, run)

            _require_memory("load OCR models")

            logger.info(
                "Pipeline run %s started for image %s",
                run_id, run.input_image_path,
            )

            engine = OCREngine(
                config=app_config,
                ocr_config=model_configs,
                preprocess_config=preprocess_raw,
                llm_config=llm_cfg,
            )

            await _check_cancelled(session, run_uuid)

            pipeline_result = engine.process(run.input_image_path, enable_llm=enable_llm)

            image_hash = hash_bytes(image_path.read_bytes())
            await _cache_ocr_results(
                session, pipeline_result.ocr_results, ocr_models_snapshot, image_hash,
            )

            await save_pipeline_results(session, run.id, pipeline_result, llm_config=llm_cfg)
            await _finalize_run(session, run, RunStatus.COMPLETED)
            logger.info("Pipeline run %s completed successfully", run_id)

        except RunCancelled:
            await _finalize_run(session, run, RunStatus.CANCELLED)
            logger.info("Pipeline run %s cancelled", run_id)

        except PermanentError as e:
            await _finalize_run(session, run, RunStatus.FAILED, str(e))
            logger.error("Pipeline run %s failed permanently: %s", run_id, e)

        except Exception as e:
            await _finalize_run(session, run, RunStatus.FAILED, str(e))
            logger.error("Pipeline run %s failed (will retry): %s", run_id, e)
            raise
