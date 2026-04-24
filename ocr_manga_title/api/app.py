from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ocr_manga_title.api.routes import (
    batches,
    catalog,
    inputs,
    models as models_route,
    ocr,
    pipeline,
    preprocess,
    profiles,
    results,
    run as run_route,
)
from ocr_manga_title.exceptions import (
    ConfigurationError,
    LLMExtractionError,
    MangaOCRError,
    ModelNotAvailableError,
    PermanentError,
)
from ocr_manga_title.settings import CORS_ORIGINS


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup/shutdown lifecycle."""
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="Manga OCR API",
        version="0.2.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(request: Request, exc: ConfigurationError):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "error_code": "configuration_error"},
        )

    @app.exception_handler(ModelNotAvailableError)
    async def model_not_available_handler(
        request: Request, exc: ModelNotAvailableError
    ):
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc), "error_code": "model_not_available"},
        )

    @app.exception_handler(LLMExtractionError)
    async def llm_extraction_error_handler(request: Request, exc: LLMExtractionError):
        return JSONResponse(
            status_code=502,
            content={"detail": str(exc), "error_code": "llm_extraction_error"},
        )

    @app.exception_handler(PermanentError)
    async def permanent_error_handler(request: Request, exc: PermanentError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error_code": "permanent_error"},
        )

    @app.exception_handler(MangaOCRError)
    async def manga_ocr_error_handler(request: Request, exc: MangaOCRError):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "error_code": "internal_error"},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(inputs.router, prefix="/api/v1/inputs", tags=["inputs"])
    app.include_router(pipeline.router, prefix="/api/v1/pipeline", tags=["pipeline"])
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
    return app
