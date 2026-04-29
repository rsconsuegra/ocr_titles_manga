"""LLM provider discovery API route."""

from fastapi import APIRouter

from ocr_manga_title.api.schemas.ollama import (
    LLMProviderInfo,
    LLMProvidersResponse,
)
from ocr_manga_title.services.ollama import is_ollama_configured, list_models

router = APIRouter()


@router.get("/providers", response_model=LLMProvidersResponse)
async def get_llm_providers():
    """Return available LLM providers with connection status."""
    providers = [
        LLMProviderInfo(
            name="openrouter",
            label="OpenRouter",
            available=True,
        ),
    ]

    ollama_info = LLMProviderInfo(
        name="ollama",
        label="Ollama",
        available=False,
    )
    if is_ollama_configured():
        try:
            models_list = await list_models()
            ollama_info = LLMProviderInfo(
                name="ollama",
                label="Ollama",
                available=True,
                configured=True,
                model_count=len(models_list),
            )
        except Exception:
            ollama_info = LLMProviderInfo(
                name="ollama",
                label="Ollama",
                available=False,
                configured=True,
                model_count=0,
            )
    else:
        ollama_info = LLMProviderInfo(
            name="ollama",
            label="Ollama",
            available=False,
            configured=False,
        )

    providers.append(ollama_info)
    return LLMProvidersResponse(providers=providers)
