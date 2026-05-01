"""Preprocessing execution service — shared by routes and worker."""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np

from ocr_manga_title.preprocess.base import BasePreProcessor, run_step_with_timeout
from ocr_manga_title.preprocess.registry import STEP_ORDER
from ocr_manga_title.services.image import decode_image, numpy_to_temp_file

logger = logging.getLogger(__name__)


def get_step_instance(step_name: str) -> BasePreProcessor:
    """Instantiate a preprocessing step by name."""
    from ocr_manga_title.preprocess.registry import get_step_class

    return get_step_class(step_name)()


def run_preprocessing_pipeline(
    image_data_url: str,
    steps_config: dict[str, Any],
) -> tuple[str, list[tuple[str, dict[str, Any]]]]:
    """Run preprocessing on a data URL.

    Returns ``(path, step_metadata)`` where *step_metadata* is an ordered
    list of ``(step_name, metadata_dict)`` pairs for every enabled step.
    """
    current_image = decode_image(image_data_url)
    return _run_pipeline_steps(current_image, steps_config)


def run_preprocessing_pipeline_from_array(
    image: np.ndarray,
    steps_config: dict[str, Any],
) -> tuple[str, list[tuple[str, dict[str, Any]]]]:
    """Run preprocessing on a numpy array.

    Returns ``(path, step_metadata)`` where *step_metadata* is an ordered
    list of ``(step_name, metadata_dict)`` pairs for every enabled step.
    """
    return _run_pipeline_steps(image, steps_config)


def _run_pipeline_steps(
    current_image: np.ndarray, steps_config: dict[str, Any],
) -> tuple[str, list[tuple[str, dict[str, Any]]]]:
    step_metadata: list[tuple[str, dict[str, Any]]] = []
    pipeline_start = time.monotonic()
    for step_name in STEP_ORDER:
        step_config = dict(steps_config.get(step_name, {}))
        enabled = step_config.pop("enabled", False)
        if not enabled:
            continue
        step = get_step_instance(step_name)
        step_start = time.monotonic()
        logger.info("Preprocessing: %s started", step_name)
        current_image, metadata = run_step_with_timeout(step, current_image, step_config)
        step_metadata.append((step_name, metadata))
        step_ms = int((time.monotonic() - step_start) * 1000)
        logger.info("Preprocessing: %s finished in %dms", step_name, step_ms)

    total_ms = int((time.monotonic() - pipeline_start) * 1000)
    logger.info("Preprocessing pipeline complete in %dms", total_ms)
    return numpy_to_temp_file(current_image), step_metadata
