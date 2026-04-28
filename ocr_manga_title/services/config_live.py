"""Live configuration service — reads and writes configs.toml for Ollama settings.

The Ollama URL is ephemeral (e.g. Cloudflare tunnels), so it's stored in the TOML
file on disk, not in the database. This service provides thread-safe read/write
access and invalidates the lru_cache on writes.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import tomllib

from ocr_manga_title.settings import CONFIG_PATH

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def _toml_path() -> Path:
    return Path(CONFIG_PATH)


def read_toml() -> dict:
    """Read and parse the current configs.toml."""
    p = _toml_path()
    if not p.exists():
        return {}
    return tomllib.loads(p.read_text())


def get_ollama_base_url() -> str:
    """Return the current Ollama base_url from TOML, or empty string."""
    data = read_toml()
    return data.get("ollama", {}).get("base_url", "")


def get_ollama_default_model() -> str:
    """Return the default Ollama LLM model from TOML."""
    data = read_toml()
    return data.get("ollama", {}).get("default_model", "")


def get_ollama_default_vision_model() -> str:
    """Return the default Ollama vision model from TOML."""
    data = read_toml()
    return data.get("ollama", {}).get("default_vision_model", "")


def get_ollama_config() -> dict:
    """Return the full [ollama] section from TOML."""
    return read_toml().get("ollama", {})


def write_ollama_base_url(new_url: str) -> None:
    """Update the ``ollama.base_url`` value in configs.toml.

    Writes a clean TOML file by re-serialising all sections.
    Invalidates the ``load_config`` lru_cache so the next read picks up the change.
    """
    with _lock:
        data = read_toml()
        if "ollama" not in data:
            data["ollama"] = {}
        data["ollama"]["base_url"] = new_url
        _write_toml(data)
        _invalidate_config_cache()


def write_ollama_models(
    default_model: str | None = None,
    default_vision_model: str | None = None,
) -> None:
    """Update default model settings in configs.toml.

    Invalidates the ``load_config`` lru_cache so the next read picks up the change.
    """
    with _lock:
        data = read_toml()
        if "ollama" not in data:
            data["ollama"] = {}
        if default_model is not None:
            data["ollama"]["default_model"] = default_model
        if default_vision_model is not None:
            data["ollama"]["default_vision_model"] = default_vision_model
        _write_toml(data)
        _invalidate_config_cache()


def _write_toml(data: dict) -> None:
    p = _toml_path()
    lines = _serialise_toml(data)
    p.write_text(lines + "\n")
    logger.info("Updated %s with new ollama.base_url", p)


def _serialise_toml(data: dict) -> str:
    """Minimal TOML serialiser for the flat structure used by configs.toml."""
    lines: list[str] = []
    top_level = {k: v for k, v in data.items() if not isinstance(v, dict)}
    sections = {k: v for k, v in data.items() if isinstance(v, dict)}

    for key, value in top_level.items():
        lines.append(f'{key} = {_toml_value(value)}')

    for section_name, section_data in sections.items():
        lines.append("")
        lines.append(f"[{section_name}]")
        for key, value in section_data.items():
            lines.append(f'{key} = {_toml_value(value)}')

    return "\n".join(lines)


def _toml_value(value) -> str:
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, int):
        return str(value)
    return repr(value)


def _invalidate_config_cache() -> None:
    from ocr_manga_title.config import load_config

    load_config.cache_clear()


async def ping_ollama(base_url: str) -> tuple[bool, str]:
    """Ping an Ollama instance to verify connectivity."""
    import httpx

    url = base_url.rstrip("/") + "/api/tags"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                model_count = len(data.get("models", []))
                return True, f"Connected — {model_count} model(s) available"
            return False, f"Unexpected status: {resp.status_code}"
    except httpx.ConnectError:
        return False, "Connection refused"
    except httpx.TimeoutException:
        return False, "Connection timed out"
    except Exception as e:
        return False, f"Error: {e}"
