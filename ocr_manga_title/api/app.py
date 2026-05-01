import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ocr_manga_title.api.routes.config import (
    catalog,
    llm as llm_route,
    ollama as ollama_route,
    profiles,
    settings as settings_route,
)
from ocr_manga_title.api.routes.ocr import (
    models as models_route,
    ocr,
    preprocess,
)
from ocr_manga_title.api.routes.pipeline import (
    batches,
    inputs,
    results,
    run as run_route,
    runs,
)
from ocr_manga_title.exceptions import (
    ConfigurationError,
    LLMExtractionError,
    MangaOCRError,
    ModelNotAvailableError,
    PermanentError,
)
from ocr_manga_title.settings import CACHE_SWEEPER_INTERVAL_SECONDS, CORS_ORIGINS

logger = logging.getLogger(__name__)


async def _cache_sweeper() -> None:
    from ocr_manga_title.db.session import async_session_factory
    from ocr_manga_title.services.cache import evict_expired

    try:
        while True:
            await asyncio.sleep(CACHE_SWEEPER_INTERVAL_SECONDS)
            try:
                async with async_session_factory() as session:
                    await evict_expired(session)
                    await session.commit()
            except Exception as e:
                logger.warning("Cache sweeper error: %s", e)
    except asyncio.CancelledError:
        pass


def _run_warmup() -> None:
    import warnings

    from ocr_manga_title.services.warmup import warmup_models

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        warmed = warmup_models()
    logger.info("Startup warmup finished: %s", warmed)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup/shutdown lifecycle: warmup, secret check, cache sweeper."""
    from ocr_manga_title.settings import SERVER_SECRET

    if not SERVER_SECRET:
        logger.warning("SERVER_SECRET is empty — credentials will not be encrypted")

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _run_warmup)
    task = asyncio.create_task(_cache_sweeper())
    yield
    with contextlib.suppress(asyncio.CancelledError):
        task.cancel()
        await task


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="Manga OCR API",
        version="0.4.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc), "error_code": "configuration_error"},
        )

    @app.exception_handler(ModelNotAvailableError)
    async def model_not_available_handler(
        request: Request, exc: ModelNotAvailableError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": str(exc), "error_code": "model_not_available"},
        )

    @app.exception_handler(LLMExtractionError)
    async def llm_extraction_error_handler(request: Request, exc: LLMExtractionError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": str(exc), "error_code": "llm_extraction_error"},
        )

    @app.exception_handler(PermanentError)
    async def permanent_error_handler(request: Request, exc: PermanentError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error_code": "permanent_error"},
        )

    @app.exception_handler(MangaOCRError)
    async def manga_ocr_error_handler(request: Request, exc: MangaOCRError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc), "error_code": "internal_error"},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(inputs.router, prefix="/api/v1/inputs", tags=["inputs"])
    app.include_router(runs.router, prefix="/api/v1/pipeline", tags=["pipeline"])
    app.include_router(results.router, prefix="/api/v1/results", tags=["results"])
    app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["catalog"])
    app.include_router(models_route.router, prefix="/api/v1/models", tags=["models"])
    app.include_router(
        preprocess.router, prefix="/api/v1/preprocess", tags=["preprocess"]
    )
    app.include_router(ocr.router, prefix="/api/v1/ocr", tags=["ocr"])
    app.include_router(run_route.router, prefix="/api/v1/run", tags=["run"])
    app.include_router(batches.router, prefix="/api/v1/batches", tags=["batches"])
    app.include_router(
        profiles.router, prefix="/api/v1/profiles", tags=["profiles"]
    )
    app.include_router(
        ollama_route.router, prefix="/api/v1/ollama", tags=["ollama"]
    )
    app.include_router(
        llm_route.router, prefix="/api/v1/llm", tags=["llm"]
    )
    app.include_router(
        settings_route.router, prefix="/api/v1/settings", tags=["settings"]
    )
    return app
