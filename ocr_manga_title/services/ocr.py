"""OCR model execution service — shared by playground, quick run, and worker."""

import time

from ocr_manga_title.api.schemas.ocr import LLMResultData, OCRResultData
from ocr_manga_title.engine.registry import MODEL_REGISTRY, get_model


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
    if isinstance(languages, list):
        pass
    elif isinstance(languages, str) and "+" in languages:
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

    start = time.monotonic()
    try:
        ocr_result = instance.run(image_path)
        return OCRResultData(
            raw_text=ocr_result.raw_text,
            model_name=ocr_result.model_name,
            confidence=ocr_result.confidence,
            processing_time_ms=ocr_result.processing_time_ms,
            error=ocr_result.error,
        )
    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
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


def run_llm_extraction(raw_text: str) -> LLMResultData:
    """Run LLM extraction on raw OCR text.

    Returns :class:`LLMResultData` (or failure placeholder).
    """
    try:
        from ocr_manga_title.config import load_config
        from ocr_manga_title.postprocess.llm_extractor import LLMExtractor

        config = load_config("config/configs.toml")
        extractor = LLMExtractor(config.openrouter)
        extracted = extractor.extract(raw_text)
        return LLMResultData(
            title_en=extracted.title_en,
            title_ja=extracted.title_ja,
            code=extracted.code,
            confidence=extracted.confidence,
            source_method=extracted.source_method,
        )
    except Exception:
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
        return False
