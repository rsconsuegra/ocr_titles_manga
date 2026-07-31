"""Process-wide cache of OCR model instances.

Keeps heavy model adapters (and their loaded weights) alive for the lifetime of
a process so that weights are loaded from disk once, not on every request.

Thread-safe: safe to call from :func:`asyncio.to_thread` (API path) and from
Dramatiq worker threads. Keyed by model ``name``; one instance per model.
"""

from __future__ import annotations

import contextlib
import io
import logging
import threading
import warnings
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ocr_manga_title.engine.base import BaseOCRModel
    from ocr_manga_title.schemas import ModelConfig

logger = logging.getLogger(__name__)

_models: dict[str, BaseOCRModel] = {}
_lock = threading.Lock()


class _QuietStdout(io.TextIOBase):
    def write(self, *_args: Any) -> None:  # type: ignore[override]
        pass

    def flush(self) -> None:
        pass


def get_cached_model(name: str) -> BaseOCRModel | None:
    """Return the cached instance for *name*, or ``None`` if not yet built."""
    return _models.get(name)


def _build(model_cls: type[BaseOCRModel], config: ModelConfig) -> BaseOCRModel:
    instance = model_cls(config)
    if instance.is_available:
        with contextlib.redirect_stdout(_QuietStdout()):  # type: ignore[type-var]
            warnings.filterwarnings("ignore", category=SyntaxWarning)
            instance.warmup()
    return instance


def get_or_create_model(
    name: str,
    model_cls: type[BaseOCRModel],
    config: ModelConfig,
) -> BaseOCRModel:
    """Return the cached instance for *name*, building + warming it on first use.

    Subsequent calls reuse the existing instance (and its in-memory weights)
    regardless of *config* — model parameters are expected to be stable across
    requests for a given model name. The first caller bears the one-time load
    cost; all later callers pay only inference cost.
    """
    cached = _models.get(name)
    if cached is not None:
        return cached

    with _lock:
        cached = _models.get(name)
        if cached is not None:
            return cached
        instance = _build(model_cls, config)
        _models[name] = instance
        logger.info("Model '%s' cached for process lifetime", name)
        return instance


def clear_cache() -> None:
    """Drop all cached model instances. Mainly useful for tests."""
    with _lock:
        _models.clear()
