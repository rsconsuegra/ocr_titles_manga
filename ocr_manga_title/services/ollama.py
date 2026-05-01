"""Ollama HTTP client — model discovery and chat completions via native API."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {"models": [], "ts": 0.0, "vision": [], "vision_ts": 0.0}
_cache_lock = threading.Lock()
_CACHE_TTL = 300.0
_HTTP_TIMEOUT = 30.0


def is_ollama_configured() -> bool:
    """Return True if the Ollama base URL is set."""
    return bool(_get_base_url())


def _get_base_url() -> str:
    from ocr_manga_title.services.config_live import get_ollama_base_url

    return get_ollama_base_url()


def _base() -> str:
    url = _get_base_url()
    return url.rstrip("/") if url else ""


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    from ocr_manga_title.settings import OLLAMA_API_KEY

    if OLLAMA_API_KEY:
        h["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
    return h


def invalidate_cache() -> None:
    """Clear the in-process Ollama model list cache."""
    with _cache_lock:
        _cache["models"] = []
        _cache["ts"] = 0.0
        _cache["vision"] = []
        _cache["vision_ts"] = 0.0


async def list_models() -> list[dict[str, Any]]:
    """GET /api/tags — list available Ollama models with metadata."""
    if not is_ollama_configured():
        return []

    now = time.monotonic()
    with _cache_lock:
        if _cache["models"] and (now - _cache["ts"]) < _CACHE_TTL:
            return _cache["models"]  # type: ignore[no-any-return]

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(
                f"{_base()}/api/tags",
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            with _cache_lock:
                _cache["models"] = models
                _cache["ts"] = now
            return models  # type: ignore[no-any-return]
    except httpx.HTTPError as e:
        logger.warning("Failed to list Ollama models: %s", e)
        return []


async def get_model_capabilities(model_name: str) -> list[str]:
    """POST /api/show — return the capabilities list for a model."""
    if not is_ollama_configured():
        return []

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(
                f"{_base()}/api/show",
                json={"name": model_name},
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("capabilities", [])  # type: ignore[no-any-return]
    except httpx.HTTPError as e:
        logger.warning("Failed to get capabilities for %s: %s", model_name, e)
        return []


async def list_vision_models() -> list[dict[str, Any]]:
    """List Ollama models that have vision capability.

    Returns list of dicts with ``name``, ``size``, ``modified_at`` keys.
    Results are cached for ``_CACHE_TTL`` seconds.
    """
    if not is_ollama_configured():
        return []

    now = time.monotonic()
    with _cache_lock:
        if _cache["vision"] and (now - _cache["vision_ts"]) < _CACHE_TTL:
            return _cache["vision"]  # type: ignore[no-any-return]

    models = await list_models()

    async def _check_vision(m: dict[str, Any]) -> dict[str, Any] | None:
        name = m.get("name", "")
        caps = await get_model_capabilities(name)
        if "vision" in caps:
            return {
                "name": name,
                "size": m.get("size", 0),
                "modified_at": m.get("modified_at", ""),
            }
        return None

    results = await asyncio.gather(*[_check_vision(m) for m in models])
    vision_models = [r for r in results if r is not None]

    with _cache_lock:
        _cache["vision"] = vision_models
        _cache["vision_ts"] = now
    return vision_models


async def chat_completion(
    model: str,
    messages: list[dict[str, Any]],
    *,
    images: list[str] | None = None,
    format: dict[str, Any] | str | None = None,
    temperature: float = 0.1,
    timeout: float | None = None,
) -> dict[str, Any]:
    """POST /api/chat — non-streaming chat completion.

    Args:
        model: Ollama model name (e.g. "llava", "llama3").
        messages: List of message dicts with role/content.
        images: Optional list of base64-encoded images to attach.
        format: JSON schema or "json" for structured output.
        temperature: Sampling temperature.
        timeout: Request timeout in seconds (defaults to OLLAMA_TIMEOUT).

    Returns:
        Response dict with ``message.content`` and metadata.

    """
    if not is_ollama_configured():
        raise RuntimeError("Ollama is not configured (OLLAMA_BASE_URL is empty)")

    if images and messages:
        messages = _inject_images(messages, images)

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if format is not None:
        payload["format"] = format

    from ocr_manga_title.settings import OLLAMA_TIMEOUT

    effective_timeout = timeout or OLLAMA_TIMEOUT

    async with httpx.AsyncClient(timeout=effective_timeout) as client:
        resp = await client.post(
            f"{_base()}/api/chat",
            json=payload,
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

def _inject_images(
    messages: list[dict[str, Any]],
    images: list[str],
) -> list[dict[str, Any]]:
    out = []
    for msg in messages:
        m = dict(msg)
        if m.get("role") == "user":
            m["images"] = images
        out.append(m)
    return out


def chat_completion_sync(
    model: str,
    messages: list[dict[str, Any]],
    *,
    images: list[str] | None = None,
    format: dict[str, Any] | str | None = None,
    temperature: float = 0.1,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Provide synchronous chat completion via ``httpx.Client``."""
    if not is_ollama_configured():
        raise RuntimeError("Ollama is not configured (OLLAMA_BASE_URL is empty)")

    if images and messages:
        messages = _inject_images(messages, images)

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if format is not None:
        payload["format"] = format

    from ocr_manga_title.settings import OLLAMA_TIMEOUT

    effective_timeout = timeout or OLLAMA_TIMEOUT

    with httpx.Client(timeout=effective_timeout) as client:
        resp = client.post(
            f"{_base()}/api/chat",
            json=payload,
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]
