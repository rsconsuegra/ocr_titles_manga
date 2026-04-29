import contextlib
import logging
import warnings

from ocr_manga_title.engine.registry import MODEL_REGISTRY
from ocr_manga_title.schemas import ModelConfig

logger = logging.getLogger(__name__)

_LOCAL_MODELS = {"paddle", "easyocr", "tesseract"}


class _QuietStdout:
    def write(self, *_args):
        pass

    def flush(self):
        pass


def _warmup_model(name: str, descriptor) -> bool:
    config = ModelConfig(
        name=name,
        enabled=True,
        language="eng",
        parameters={p.name: p.default for p in descriptor.params},
    )
    try:
        instance = descriptor.model_cls(config)
        if not instance.is_available:
            logger.info("Model '%s' not available, skipping warmup", name)
            return False

        with contextlib.redirect_stdout(_QuietStdout()):
            warnings.filterwarnings("ignore", category=SyntaxWarning)
            instance.warmup()

        logger.info("Model '%s' warmed up successfully", name)
        return True
    except Exception as e:
        logger.warning("Model '%s' warmup failed: %s", name, e)
        return False


def warmup_models() -> list[str]:
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
