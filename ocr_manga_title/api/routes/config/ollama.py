"""Ollama integration API routes — model discovery and status."""

from fastapi import APIRouter

from ocr_manga_title.api.schemas.ollama import (
    OllamaLLMModelResponse,
    OllamaStatusResponse,
    OllamaVisionModelResponse,
)
from ocr_manga_title.services.config_live import (
    get_ollama_base_url,
    get_ollama_default_model,
    get_ollama_default_vision_model,
)
from ocr_manga_title.services.ollama import (
    is_ollama_configured,
    list_models,
    list_vision_models,
    map_llm_models,
    map_vision_models,
)

router = APIRouter()


@router.get("/status", response_model=OllamaStatusResponse)
async def get_ollama_status() -> OllamaStatusResponse:
    """Return whether Ollama is configured, the base URL, and default models."""
    return OllamaStatusResponse(
        configured=is_ollama_configured(),
        base_url=get_ollama_base_url(),
        default_model=get_ollama_default_model(),
        default_vision_model=get_ollama_default_vision_model(),
    )


@router.get("/vision-models", response_model=list[OllamaVisionModelResponse])
async def get_vision_models() -> list[OllamaVisionModelResponse]:
    """List Ollama models that have vision capability."""
    models = await list_vision_models()
    return [OllamaVisionModelResponse(**m) for m in map_vision_models(models)]


@router.get("/llm-models", response_model=list[OllamaLLMModelResponse])
async def get_llm_models() -> list[OllamaLLMModelResponse]:
    """List all available Ollama models (usable for LLM extraction)."""
    models = await list_models()
    return [OllamaLLMModelResponse(**m) for m in map_llm_models(models)]
