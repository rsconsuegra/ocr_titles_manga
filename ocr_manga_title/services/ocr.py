"""OCR model execution service — shared by playground, quick run, and worker."""

import logging
import time

from ocr_manga_title.api.schemas.ocr import LLMResultData, OCRResultData, TextBlockData
from ocr_manga_title.engine.registry import MODEL_REGISTRY, get_model

logger = logging.getLogger(__name__)


def build_model_config(model_name: str, overrides: dict) -> tuple | None:
    """Merge registry defaults with user overrides into a (ModelConfig, model_cls) tuple.

    Returns ``None`` if the model is not in the registry.
    """
    from ocr_manga_title.schemas import ModelConfig

    descriptor = get_model(model_name)
    if descriptor is None:
        return None

    merged_params = {p.name: p.default for p in descriptor.params}
    merged_params.update(overrides)

    languages = merged_params.pop("languages", "eng")
    if isinstance(languages, str) and "+" in languages:
        languages = languages.split("+")

    config = ModelConfig(
        name=model_name,
        enabled=True,
        language=languages,
        parameters=merged_params,
    )
    return config, descriptor.model_cls


def run_single_model(
    model_name: str,
    image_path: str,
    overrides: dict | None = None,
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
        instance = model_cls(config)
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
        return OCRResultData(
            raw_text=ocr_result.raw_text,
            model_name=ocr_result.model_name,
            confidence=ocr_result.confidence,
            processing_time_ms=ocr_result.processing_time_ms,
            error=ocr_result.error,
            blocks=(
                [
                    TextBlockData(
                        bbox=b.bbox, text=b.text, confidence=b.confidence
                    )
                    for b in ocr_result.blocks
                ]
                if ocr_result.blocks
                else None
            ),
        )
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
    ocr_config: dict,
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


def run_llm_extraction(
    raw_text: str,
    *,
    provider: str | None = None,
    llm_model: str | None = None,
    llm_config: dict | None = None,
) -> LLMResultData:
    """Run LLM extraction on raw OCR text.

    Selects the LLM provider based on the *provider* argument (falls back to
    ``llm_provider`` in configs.toml when *None*).
    Returns :class:`LLMResultData` (or failure placeholder).
    """
    try:
        from ocr_manga_title.config import load_config, load_openrouter_models
        from ocr_manga_title.postprocess.llm_extractor import LLMExtractor
        from ocr_manga_title.schemas import LLMPromptConfig

        config = load_config("config/configs.toml")
        effective_provider = provider or config.llm_provider

        prompt_config = LLMPromptConfig.from_dict(llm_config)

        extractor = LLMExtractor(
            openrouter_config=config.openrouter if effective_provider == "openrouter" else None,
            ollama_config=config.ollama if effective_provider == "ollama" else None,
            provider=effective_provider,
            prompt_config=prompt_config,
        )
        llm_start = time.monotonic()
        effective_model = llm_model
        if not effective_model and prompt_config and prompt_config.llm_model:
            effective_model = prompt_config.llm_model
        logger.info("LLM extraction started (provider=%s, model=%s)", effective_provider, effective_model)
        supports_json = True
        if effective_model and effective_provider == "openrouter":
            models_list = load_openrouter_models()
            model_info = next((m for m in models_list if m.get("id") == effective_model), {})
            supports_json = model_info.get("supports_json_mode", True)
        extracted = extractor.extract(raw_text, model=effective_model, supports_json_mode=supports_json)
        llm_ms = int((time.monotonic() - llm_start) * 1000)
        logger.info("LLM extraction finished in %dms", llm_ms)
        return LLMResultData(
            title_en=extracted.title_en,
            title_ja=extracted.title_ja,
            code=extracted.code,
            confidence=extracted.confidence,
            source_method=extracted.source_method,
            raw_response=extracted.raw_response,
        )
    except Exception:
        logger.warning("LLM extraction failed", exc_info=True)
        return LLMResultData(confidence=0.0, source_method="llm_failed")


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
            language="eng",
            parameters=(
                {
                    k: v.default
                    for k, v in {p.name: p for p in descriptor.params}.items()
                }
                if descriptor.params
                else {}
            ),
        )
        instance = descriptor.model_cls(cfg)
        return instance.is_available
    except Exception:
        logger.debug("Model availability check failed for %s", model_name, exc_info=True)
        return False
