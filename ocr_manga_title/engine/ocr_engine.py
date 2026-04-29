"""Core OCR engine that orchestrates multi-model extraction and post-processing."""

from __future__ import annotations

import logging
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.engine.registry import MODEL_REGISTRY
from ocr_manga_title.exceptions import LLMExtractionError
from ocr_manga_title.postprocess.llm_extractor import LLMExtractor
from ocr_manga_title.postprocess.rule_matcher import RuleMatcher
from ocr_manga_title.schemas import (
    AppConfig,
    ExtractedTitle,
    ModelConfig,
    OCRResult,
    PipelineResult,
)
from ocr_manga_title.settings import ALLOWED_EXTENSIONS

logger = logging.getLogger(__name__)


def _build_prompt_config(llm_config: dict | None) -> LLMPromptConfig:
    from ocr_manga_title.schemas import LLMPromptConfig

    return LLMPromptConfig.from_dict(llm_config)


class OCREngine:
    """Orchestrates OCR model execution, LLM extraction, and rule-based post-processing.

    Given an application config and per-model config, the engine initializes all
    enabled and available OCR models, then for each image runs them in parallel,
    feeds raw text through the LLM extractor and rule matcher, and returns the
    best extracted title.
    """

    SUPPORTED_FORMATS = frozenset(ALLOWED_EXTENSIONS)

    def __init__(
        self,
        config: AppConfig,
        ocr_config: dict[str, ModelConfig],
        preprocess_config: dict | None = None,
        llm_config: dict | None = None,
    ):
        self._config = config
        self._ocr_config = ocr_config
        self._models: list[BaseOCRModel] = self._initialize_models()
        self._prompt_config = _build_prompt_config(llm_config)
        self._llm_extractor = LLMExtractor(
            openrouter_config=config.openrouter if config.llm_provider == "openrouter" else None,
            ollama_config=config.ollama if config.llm_provider == "ollama" else None,
            provider=config.llm_provider,
            prompt_config=self._prompt_config,
        )
        self._rule_matcher = RuleMatcher()
        self._preprocess_pipeline = None
        self._temp_dir: tempfile.TemporaryDirectory | None = None

        if preprocess_config:
            pp_settings = preprocess_config.get("preprocessing", {})
            if pp_settings.get("enabled", False):
                from ocr_manga_title.preprocess import PreProcessingPipeline

                self._preprocess_pipeline = PreProcessingPipeline(
                    preprocess_config
                )
                self._temp_dir = tempfile.TemporaryDirectory(prefix="manga_ocr_")
                logger.info("Preprocessing pipeline enabled")

        logger.info(
            "OCREngine initialized with %d models: %s",
            len(self._models),
            [m.name for m in self._models],
        )

    def _initialize_models(self) -> list[BaseOCRModel]:
        models: list[BaseOCRModel] = []
        skipped: list[str] = []

        for name, config in self._ocr_config.items():
            if not config.enabled:
                logger.info("Model '%s' is disabled, skipping", name)
                skipped.append(f"{name} (disabled)")
                continue

            descriptor = MODEL_REGISTRY.get(name)
            if descriptor is None:
                logger.warning("Unknown model '%s' in config, skipping", name)
                skipped.append(f"{name} (unknown)")
                continue

            try:
                model = descriptor.model_cls(config)
            except (ImportError, RuntimeError) as e:
                logger.error("Failed to instantiate model '%s': %s", name, e)
                skipped.append(f"{name} (init error)")
                continue

            if not model.is_available:
                logger.info("Model '%s' is not available, skipping", name)
                skipped.append(f"{name} (not available)")
                continue

            models.append(model)

        if not models:
            logger.warning(
                "No OCR models available. Pipeline will produce empty results."
            )

        logger.info(
            "Initialized %d models: %s. Skipped: %s",
            len(models),
            [m.name for m in models],
            skipped,
        )
        return models

    def _run_single_model(self, model: BaseOCRModel, image_path: str) -> OCRResult:
        logger.info("OCR model '%s' started", model.name)
        start = time.monotonic()
        try:
            result = model.run(image_path)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.info("OCR model '%s' finished in %dms", model.name, elapsed_ms)
            return result
        except FileNotFoundError:
            raise
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.info("OCR model '%s' failed in %dms: %s", model.name, elapsed_ms, e)
            return OCRResult(
                raw_text="",
                model_name=model.name,
                confidence=0.0,
                processing_time_ms=elapsed_ms,
                error=str(e),
            )

    def _run_models(self, image_path: str) -> tuple[list[OCRResult], list[str]]:
        ocr_results: list[OCRResult] = []
        errors: list[str] = []

        if len(self._models) <= 1:
            for model in self._models:
                result = self._run_single_model(model, image_path)
                ocr_results.append(result)
                if result.error is not None:
                    errors.append(f"Model {model.name} failed: {result.error}")
                    logger.error("Model %s failed: %s", model.name, result.error)
        else:
            with ThreadPoolExecutor(max_workers=len(self._models)) as pool:
                futures = {
                    pool.submit(self._run_single_model, model, image_path): model
                    for model in self._models
                }
                file_not_found = False
                for future in as_completed(futures):
                    model = futures[future]
                    try:
                        result = future.result()
                        ocr_results.append(result)
                        if result.error is not None:
                            errors.append(f"Model {model.name} failed: {result.error}")
                            logger.error("Model %s failed: %s", model.name, result.error)
                    except FileNotFoundError:
                        if not file_not_found:
                            errors.append(f"Image not found for {model.name}")
                            logger.error("Image not found: %s", image_path)
                        file_not_found = True
                        for f in futures:
                            f.cancel()
                    except Exception as e:
                        errors.append(f"Model {model.name} failed: {e}")
                        logger.error(
                            "Model %s failed: %s", model.name, e, exc_info=True
                        )
                if file_not_found:
                    raise FileNotFoundError(f"Image not found: {image_path}")

        return ocr_results, errors

    def _llm_extract_from_results(
        self,
        ocr_results: list[OCRResult],
        errors: list[str],
    ) -> list[ExtractedTitle]:
        extracted_titles: list[ExtractedTitle] = []

        for result in ocr_results:
            if result.error is not None or not result.raw_text.strip():
                continue

            llm_start = time.monotonic()
            try:
                logger.info("LLM extraction started for model '%s'", result.model_name)
                extracted = self._llm_extractor.extract(result.raw_text)
                llm_ms = int((time.monotonic() - llm_start) * 1000)
                logger.info("LLM extraction finished for model '%s' in %dms", result.model_name, llm_ms)
            except LLMExtractionError as e:
                llm_ms = int((time.monotonic() - llm_start) * 1000)
                errors.append(f"LLM extraction failed for {result.model_name}: {e}")
                logger.error("LLM extraction failed for %s in %dms: %s", result.model_name, llm_ms, e)
                continue

            try:
                extracted = self._rule_matcher.augment(extracted, result.raw_text)
            except (ValueError, AttributeError) as e:
                errors.append(f"Rule matching failed for {result.model_name}: {e}")
                logger.error("Rule matching failed for %s: %s", result.model_name, e)

            extracted_titles.append(extracted)

        return extracted_titles

    def _fallback_rule_match(
        self,
        ocr_results: list[OCRResult],
        errors: list[str],
    ) -> list[ExtractedTitle]:
        fallback_titles: list[ExtractedTitle] = []

        for result in ocr_results:
            if result.error is None and result.raw_text.strip():
                try:
                    rule_result = self._rule_matcher.match(result.raw_text)
                    if rule_result.code is not None:
                        rule_result.source_model = result.model_name
                        fallback_titles.append(rule_result)
                except (ValueError, AttributeError) as e:
                    errors.append(
                        f"Rule matching failed for {result.model_name}: {e}"
                    )

        return fallback_titles

    def _extract_titles(
        self,
        ocr_results: list[OCRResult],
        errors: list[str],
    ) -> list[ExtractedTitle]:
        titles = self._llm_extract_from_results(ocr_results, errors)

        if not titles or all(t.confidence == 0.0 for t in titles):
            titles.extend(self._fallback_rule_match(ocr_results, errors))

        return titles

    @staticmethod
    def _select_best(titles: list[ExtractedTitle]) -> ExtractedTitle | None:
        if not titles:
            return None
        candidate = max(titles, key=lambda t: t.confidence)
        return candidate if candidate.confidence > 0.0 else None

    def process(
        self, image_path: str, *, enable_llm: bool = True
    ) -> PipelineResult:
        """Run the full OCR pipeline on a single image.

        Args:
            image_path: Path to the image file to process.

        Returns:
            :class:`~ocr_manga_title.schemas.PipelineResult` containing all OCR results,
            the best extracted title (or ``None``), and any accumulated errors.

        Raises:
            FileNotFoundError: If *image_path* does not exist.
            ValueError: If the image format is not in :attr:`SUPPORTED_FORMATS`.

        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported image format: {path.suffix}")

        pipeline_start = time.monotonic()
        logger.info("Pipeline started for %s", image_path)

        preprocess_result = None
        ocr_image_path = image_path

        if self._preprocess_pipeline:
            preprocess_result = self._preprocess_pipeline.process(image_path)
            if preprocess_result.output_path:
                ocr_image_path = preprocess_result.output_path
                logger.info("Using preprocessed image: %s", ocr_image_path)
            else:
                logger.warning("Preprocessing produced no output, using original image")

        ocr_results, errors = self._run_models(ocr_image_path)

        if preprocess_result and preprocess_result.steps:
            from ocr_manga_title.preprocess.transform import CoordinateTransform
            step_meta = [
                (s.step_name, s.metadata)
                for s in preprocess_result.steps
                if s.enabled and s.success and s.metadata
            ]
            if step_meta:
                transform = CoordinateTransform.from_pipeline(step_meta)
                for ocr_result in ocr_results:
                    if ocr_result.blocks:
                        for block in ocr_result.blocks:
                            block.bbox = transform.inverse_map_bbox(block.bbox)

        extracted_titles = (
            self._extract_titles(ocr_results, errors) if enable_llm else []
        )
        best = self._select_best(extracted_titles)

        pipeline_ms = int((time.monotonic() - pipeline_start) * 1000)
        logger.info("Pipeline complete in %dms", pipeline_ms)

        return PipelineResult(
            input_path=str(image_path),
            ocr_results=ocr_results,
            extracted=best,
            timestamp=datetime.now(),
            errors=errors,
            preprocess_result=preprocess_result,
        )

    def cleanup(self) -> None:
        """Clean up temporary resources including preprocessed images."""
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None

    def __enter__(self):  # noqa: D105
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # noqa: D105
        self.cleanup()
        return False
