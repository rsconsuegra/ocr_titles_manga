"""Ollama integration API routes — model discovery and status."""

from fastapi import APIRouter

from ocr_manga_title.services.config_live import (
    get_ollama_base_url,
    get_ollama_default_model,
    get_ollama_default_vision_model,
)
from ocr_manga_title.services.ollama import (
    is_ollama_configured,
    list_models,
    list_vision_models,
)

router = APIRouter()


@router.get("/status")
async def get_ollama_status():
    """Return whether Ollama is configured, the base URL, and default models."""
    return {
        "configured": is_ollama_configured(),
        "base_url": get_ollama_base_url(),
        "default_model": get_ollama_default_model(),
        "default_vision_model": get_ollama_default_vision_model(),
    }


@router.get("/vision-models")
async def get_vision_models():
    """List Ollama models that have vision capability."""
    return await list_vision_models()


@router.get("/llm-models")
async def get_llm_models():
    """List all available Ollama models (usable for LLM extraction)."""
    models = await list_models()
    return [
        {
            "name": m.get("name", ""),
            "size": m.get("size", 0),
            "modified_at": m.get("modified_at", ""),
            "parameter_size": m.get("details", {}).get("parameter_size", ""),
            "quantization": m.get("details", {}).get("quantization", ""),
        }
        for m in models
    ]
