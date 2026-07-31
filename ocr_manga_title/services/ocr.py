"""OCR model execution service — shared by playground, quick run, and worker."""

import logging
import time
from typing import Any

from ocr_manga_title.api.schemas.ocr import LLMResultData, OCRResultData, TextBlockData
from ocr_manga_title.engine.registry import MODEL_REGISTRY, get_model, registry_defaults
from ocr_manga_title.schemas import ExtractedTitle, OCRResult
from ocr_manga_title.settings import CONFIG_PATH

logger = logging.getLogger(__name__)


def pick_best[T: (OCRResult, OCRResultData)](results: list[T]) -> T | None:
    """Return highest-confidence result with non-empty text and no error."""
    return next(
        (
            r
            for r in sorted(results, key=lambda r: r.confidence, reverse=True)
            if r.raw_text.strip() and not r.error
        ),
        None,
    )


def _parse_languages(languages: str | list[str]) -> list[str]:
    """Normalize language parameter to a list."""
    if isinstance(languages, str):
        return languages.split("+") if "+" in languages else [languages]
    return languages


def ocr_result_to_data(ocr_result: OCRResult) -> OCRResultData:
    """Convert an internal :class:`OCRResult` to the API-layer :class:`OCRResultData`."""
    return OCRResultData(
        raw_text=ocr_result.raw_text,
        model_name=ocr_result.model_name,
        confidence=ocr_result.confidence,
        processing_time_ms=ocr_result.processing_time_ms,
        error=ocr_result.error,
        blocks=(
            [
                TextBlockData(bbox=b.bbox, text=b.text, confidence=b.confidence)
                for b in ocr_result.blocks
            ]
            if ocr_result.blocks
            else None
        ),
    )


def build_model_config(
    model_name: str, overrides: dict[str, Any]
) -> tuple[Any, Any] | None:
    """Merge registry defaults with user overrides into a (ModelConfig, model_cls) tuple.

    Returns ``None`` if the model is not in the registry.
    """
    from ocr_manga_title.schemas import ModelConfig

    descriptor = get_model(model_name)
    if descriptor is None:
        return None

    merged_params = registry_defaults(descriptor)
    merged_params.update(overrides)

    languages = merged_params.pop("languages", "eng")
    languages = _parse_languages(languages)

    config = ModelConfig(
        name=model_name,
        enabled=True,
        parameters={**merged_params, "language": languages},
    )
    return config, descriptor.model_cls


def run_single_model(
    model_name: str,
    image_path: str,
    overrides: dict[str, Any] | None = None,
) -> OCRResultData:
    """Instantiate and run a single OCR model.

    Returns :class:`OCRResultData` with results or error.
    """
    overrides = overrides or {}
    result = build_model_config(model_name, overrides)
    if result is None:
        return OCRResultData(model_name=model_name, error="Model class not found")

    config, model_cls = result

    try:
        from ocr_manga_title.engine.cache import get_or_create_model

        instance = get_or_create_model(model_name, model_cls, config)
    except Exception as e:
        return OCRResultData(model_name=model_name, error=f"Init failed: {e}")

    if not instance.is_available:
        return OCRResultData(model_name=model_name, error="Model not available")

    logger.info("OCR model '%s' started", model_name)
    start = time.monotonic()
    try:
        ocr_result = instance.run(image_path)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info("OCR model '%s' finished in %dms", model_name, elapsed_ms)
        return ocr_result_to_data(ocr_result)
    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info("OCR model '%s' failed in %dms: %s", model_name, elapsed_ms, e)
        return OCRResultData(
            model_name=model_name,
            processing_time_ms=elapsed_ms,
            error=str(e),
        )


def run_all_enabled_models(
    image_path: str,
    ocr_config: dict[str, Any],
) -> list[OCRResultData]:
    """Run all enabled OCR models on an image.

    Returns list of :class:`OCRResultData`.
    """
    results: list[OCRResultData] = []

    for name, descriptor in MODEL_REGISTRY.items():
        override = ocr_config.get(name, {})
        if not override.get("enabled", False):
            continue

        model_cls = descriptor.model_cls
        if not model_cls:
            results.append(
                OCRResultData(model_name=name, error="Model class not found")
            )
            continue

        result = run_single_model(name, image_path, override)
        results.append(result)

    return results


def extract_title_from_text(
    raw_text: str,
    *,
    provider: str,
    llm_model: str | None = None,
    prompt_config: Any | None = None,
) -> ExtractedTitle:
    """Core LLM extraction — creates extractor, calls extract, returns ExtractedTitle.

    This is the single source of truth for LLM post-processing.
    Both the API routes and OCREngine delegate to this function.
    """
    from ocr_manga_title.config import load_config
    from ocr_manga_title.postprocess.llm_extractor import LLMExtractor

    config = load_config(CONFIG_PATH)

    extractor = LLMExtractor(
        openrouter_config=config.openrouter if provider == "openrouter" else None,
        ollama_config=config.ollama if provider == "ollama" else None,
        provider=provider,
        prompt_config=prompt_config,
    )
    effective_model = llm_model
    if not effective_model and prompt_config and prompt_config.llm_model:
        effective_model = prompt_config.llm_model

    return extractor.extract(raw_text, model=effective_model)


def run_llm_extraction(
    raw_text: str,
    *,
    provider: str | None = None,
    llm_model: str | None = None,
    llm_config: dict[str, Any] | None = None,
) -> LLMResultData:
    """Run LLM extraction on raw OCR text.

    Selects the LLM provider based on the *provider* argument (falls back to
    ``llm_provider`` in configs.toml when *None*).
    Returns :class:`LLMResultData` (or failure placeholder).
    """
    try:
        from ocr_manga_title.config import load_config
        from ocr_manga_title.schemas import LLMPromptConfig

        config = load_config(CONFIG_PATH)
        effective_provider = provider or config.llm_provider
        prompt_config = LLMPromptConfig.from_dict(llm_config)

        llm_start = time.monotonic()
        logger.info("LLM extraction started (provider=%s, model=%s)", effective_provider, llm_model)
        extracted = extract_title_from_text(
            raw_text,
            provider=effective_provider,
            llm_model=llm_model,
            prompt_config=prompt_config,
        )
        llm_ms = int((time.monotonic() - llm_start) * 1000)
        logger.info("LLM extraction finished in %dms", llm_ms)
        return LLMResultData(
            title_en=extracted.title_en,
            title_ja=extracted.title_ja,
            code=extracted.code,
            confidence=extracted.confidence,
            source_method=extracted.source_method,
            raw_response=extracted.raw_response,
            extra_metadata=extracted.extra_metadata,
        )
    except Exception as e:
        logger.warning("LLM extraction failed", exc_info=True)
        return LLMResultData(confidence=0.0, source_method="llm_failed", error=str(e))


def check_model_availability(model_name: str) -> bool:
    """Check if a model's runtime dependencies are installed."""
    from ocr_manga_title.schemas import ModelConfig

    descriptor = get_model(model_name)
    if descriptor is None:
        return False

    try:
        cfg = ModelConfig(
            name=model_name,
            enabled=True,
            parameters={
                "language": "eng",
                **registry_defaults(descriptor),
            },
        )
        instance = descriptor.model_cls(cfg)
        return instance.is_available
    except Exception:
        logger.debug("Model availability check failed for %s", model_name, exc_info=True)
        return False
