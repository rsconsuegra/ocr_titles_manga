"""Preprocessing execution service — shared by routes and worker."""

from __future__ import annotations

import logging
import time

import numpy as np

from ocr_manga_title.preprocess.base import run_step_with_timeout
from ocr_manga_title.preprocess.registry import STEP_ORDER
from ocr_manga_title.services.image import decode_image, numpy_to_temp_file

logger = logging.getLogger(__name__)


def get_step_instance(step_name: str):
    """Instantiate a preprocessing step by name."""
    from ocr_manga_title.preprocess.steps.binarize import BinarizeStep
    from ocr_manga_title.preprocess.steps.denoise import DenoiseStep
    from ocr_manga_title.preprocess.steps.grayscale import GrayscaleStep
    from ocr_manga_title.preprocess.steps.roi import ROIStep
    from ocr_manga_title.preprocess.steps.upscale import UpscaleStep

    steps_map = {
        "roi": ROIStep,
        "grayscale": GrayscaleStep,
        "upscale": UpscaleStep,
        "denoise": DenoiseStep,
        "binarize": BinarizeStep,
    }
    cls = steps_map.get(step_name)
    if cls is None:
        raise ValueError(f"Unknown step: {step_name}")
    return cls()


def run_preprocessing_pipeline(
    image_data_url: str,
    steps_config: dict,
) -> str:
    """Run preprocessing on a data URL. Returns path to processed image."""
    current_image = decode_image(image_data_url)
    return _run_pipeline_steps(current_image, steps_config)


def run_preprocessing_pipeline_from_array(
    image: np.ndarray,
    steps_config: dict,
) -> str:
    """Run preprocessing on a numpy array. Returns path to processed image."""
    return _run_pipeline_steps(image, steps_config)


def _run_pipeline_steps(current_image, steps_config: dict) -> str:
    pipeline_start = time.monotonic()
    for step_name in STEP_ORDER:
        step_config = dict(steps_config.get(step_name, {}))
        enabled = step_config.pop("enabled", False)
        if not enabled:
            continue
        step = get_step_instance(step_name)
        step_start = time.monotonic()
        logger.info("Preprocessing: %s started", step_name)
        current_image, _ = run_step_with_timeout(step, current_image, step_config)
        step_ms = int((time.monotonic() - step_start) * 1000)
        logger.info("Preprocessing: %s finished in %dms", step_name, step_ms)

    total_ms = int((time.monotonic() - pipeline_start) * 1000)
    logger.info("Preprocessing pipeline complete in %dms", total_ms)
    return numpy_to_temp_file(current_image)
