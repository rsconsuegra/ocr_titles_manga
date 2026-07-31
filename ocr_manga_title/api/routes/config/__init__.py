"""Configuration management routes (catalog, profiles, LLM, Ollama, settings)."""

from ocr_manga_title.api.routes.config import (
    catalog,
    llm as llm_route,
    ollama as ollama_route,
    profiles,
    settings as settings_route,
)

__all__ = ["catalog", "llm_route", "ollama_route", "profiles", "settings_route"]
