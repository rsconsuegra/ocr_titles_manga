"""Image denoising step with configurable methods and strength presets."""

import logging
from typing import Any

import cv2
import numpy as np

from ocr_manga_title.preprocess.base import BasePreProcessor

logger = logging.getLogger(__name__)

STRENGTH_PRESETS: dict[str, dict[str, dict[str, float]]] = {
    "gaussian": {
        "light": {"ksize": 3, "sigma": 0.5},
        "medium": {"ksize": 5, "sigma": 1.0},
        "heavy": {"ksize": 7, "sigma": 1.5},
    },
    "median": {
        "light": {"ksize": 3},
        "medium": {"ksize": 5},
        "heavy": {"ksize": 7},
    },
    "nlmeans": {
        "light": {"h": 3},
        "medium": {"h": 6},
        "heavy": {"h": 10},
    },
}


class DenoiseStep(BasePreProcessor):
    """Reduces image noise using Gaussian, median, or non-local means filtering."""

    step_name = "denoise"

    def process(self, image: np.ndarray, config: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        """Reduce image noise using the configured method and strength."""
        method: str = config.get("method", "gaussian") or "gaussian"
        strength: str = config.get("strength", "light") or "light"

        if method not in STRENGTH_PRESETS:
            logger.warning(
                "Unknown denoise method '%s', defaulting to gaussian", method
            )
            method = "gaussian"

        if strength not in STRENGTH_PRESETS[method]:
            logger.warning("Unknown strength '%s', defaulting to light", strength)
            strength = "light"

        params = STRENGTH_PRESETS[method][strength]

        if method == "gaussian":
            result = cv2.GaussianBlur(
                image, (int(params["ksize"]), int(params["ksize"])), params["sigma"]
            )
        elif method == "median":
            result = cv2.medianBlur(image, int(params["ksize"]))
        elif method == "nlmeans":
            if image.ndim == 2:
                result = cv2.fastNlMeansDenoising(image, None, h=params["h"])
            else:
                result = cv2.fastNlMeansDenoisingColored(image, None, h=params["h"])
        else:
            result = image

        return result, {"method": method, "strength": strength, "params": params}
