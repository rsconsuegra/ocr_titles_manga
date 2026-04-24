"""Grayscale conversion step for preprocessing."""

import cv2
import numpy as np

from ocr_manga_title.preprocess.base import BasePreProcessor


class GrayscaleStep(BasePreProcessor):
    """Converts BGR/BGRA images to single-channel grayscale."""

    @property
    def name(self) -> str:
        """Machine-readable identifier for this step."""
        return "grayscale"

    @property
    def is_available(self) -> bool:
        """Whether the step's runtime dependencies are installed."""
        return True

    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        """Convert an image to single-channel grayscale."""
        if image.ndim == 2:
            return image, {"original_channels": 1, "converted": False}

        channels = image.shape[2] if image.ndim == 3 else 1

        if channels == 4:
            bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        elif channels == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            return image, {"original_channels": channels, "converted": False}

        return gray, {"original_channels": channels, "converted": True}
