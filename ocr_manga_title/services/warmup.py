"""Eager loading of local OCR models on application startup."""

import contextlib
import io
import logging
import warnings
from typing import Any

from ocr_manga_title.engine.registry import (
    MODEL_REGISTRY,
    ModelDescriptor,
    registry_defaults,
)
from ocr_manga_title.schemas import ModelConfig

logger = logging.getLogger(__name__)

_LOCAL_MODELS = {"paddle", "easyocr", "tesseract"}


class _QuietStdout(io.TextIOBase):
    def write(self, *_args: Any) -> None:  # type: ignore[override]
        pass

    def flush(self) -> None:
        pass


def _warmup_model(name: str, descriptor: ModelDescriptor) -> bool:
    config = ModelConfig(
        name=name,
        enabled=True,
        parameters={**registry_defaults(descriptor), "language": "eng"},
    )
    try:
        instance = descriptor.model_cls(config)
        if not instance.is_available:
            logger.info("Model '%s' not available, skipping warmup", name)
            return False

        with contextlib.redirect_stdout(_QuietStdout()):  # type: ignore[type-var]
            warnings.filterwarnings("ignore", category=SyntaxWarning)
            instance.warmup()

        logger.info("Model '%s' warmed up successfully", name)
        return True
    except Exception as e:
        logger.warning("Model '%s' warmup failed: %s", name, e)
        return False


def warmup_models() -> list[str]:
    """Pre-load all local OCR models and return the names that succeeded."""
    warmed: list[str] = []
    logger.info("Starting model warmup...")

    for name, descriptor in MODEL_REGISTRY.items():
        if name not in _LOCAL_MODELS:
            continue
        if _warmup_model(name, descriptor):
            warmed.append(name)

    if warmed:
        logger.info("Model warmup complete: %s", warmed)
    else:
        logger.info("No models warmed up")

    return warmed
