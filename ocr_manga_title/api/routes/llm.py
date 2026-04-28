"""LLM provider discovery API route."""

from fastapi import APIRouter

from ocr_manga_title.services.ollama import is_ollama_configured, list_models

router = APIRouter()


@router.get("/providers")
async def get_llm_providers():
    """Return available LLM providers with connection status."""
    providers = [
        {
            "name": "openrouter",
            "label": "OpenRouter",
            "available": True,
        },
    ]

    ollama_info: dict = {
        "name": "ollama",
        "label": "Ollama",
        "available": False,
    }
    if is_ollama_configured():
        ollama_info["configured"] = True
        try:
            models_list = await list_models()
            ollama_info["available"] = True
            ollama_info["model_count"] = len(models_list)
        except Exception:
            ollama_info["available"] = False
            ollama_info["model_count"] = 0
    else:
        ollama_info["configured"] = False

    providers.append(ollama_info)
    return {"providers": providers}
