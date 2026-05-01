"""Image binarization step using Otsu or adaptive thresholding."""

from typing import Any

import cv2
import numpy as np

from ocr_manga_title.preprocess.base import BasePreProcessor


class BinarizeStep(BasePreProcessor):
    """Converts images to binary (black and white) for improved OCR accuracy."""

    @property
    def name(self) -> str:
        """Machine-readable identifier for this step."""
        return "binarize"

    @property
    def is_available(self) -> bool:
        """Whether the step's runtime dependencies are installed."""
        return True

    def process(self, image: np.ndarray, config: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        """Apply Otsu or adaptive thresholding to produce a binary image."""
        method = config.get("method", "otsu")
        invert = config.get("invert", False)

        if image.ndim == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        thresh_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY

        if method == "otsu":
            threshold, binary = cv2.threshold(
                image, 0, 255, thresh_type + cv2.THRESH_OTSU
            )
            return binary, {
                "method": "otsu",
                "threshold": float(threshold),
                "invert": invert,
            }

        block_size = config.get("block_size", 11)
        c = config.get("c", 2)

        if block_size < 3:
            block_size = 3
        if block_size % 2 == 0:
            block_size += 1

        if method == "adaptive_gaussian":
            binary = cv2.adaptiveThreshold(
                image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, thresh_type, block_size, c
            )
        elif method == "adaptive_mean":
            binary = cv2.adaptiveThreshold(
                image, 255, cv2.ADAPTIVE_THRESH_MEAN_C, thresh_type, block_size, c
            )
        else:
            raise ValueError(f"Unknown binarization method: {method}")

        return binary, {
            "method": method,
            "block_size": block_size,
            "c": c,
            "invert": invert,
        }
