"""Region-of-interest detection step for preprocessing."""

import logging
from typing import Any

import cv2
import numpy as np

from ocr_manga_title.preprocess.base import BasePreProcessor

logger = logging.getLogger(__name__)


class ROIStep(BasePreProcessor):
    """Detects and crops the region of interest from a manga image.

    Uses contour detection to find text-dense regions and merges overlapping
    bounding boxes into a single crop.
    """

    step_name = "roi"

    def process(self, image: np.ndarray, config: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        """Detect and crop the region of interest from the image."""
        method = config.get("method", "contour")

        h, w = image.shape[:2]
        if h < 100 or w < 100:
            logger.debug("Image too small for ROI detection, skipping")
            return image, {
                "method": method,
                "regions_detected": 0,
                "crop_performed": False,
                "reason": "image_too_small",
            }

        if method == "contour":
            return self._contour_detect(image, config)

        logger.warning("Unknown ROI method '%s', no crop performed", method)
        return image, {
            "method": method,
            "regions_detected": 0,
            "crop_performed": False,
            "reason": "unknown_method",
        }

    def _contour_detect(
        self, image: np.ndarray, config: dict[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        min_area = config.get("min_area", 500)
        padding = config.get("padding", 10)
        merge_overlap = config.get("merge_overlap", 0.3)

        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        rects: list[tuple[int, int, int, int]] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= min_area:
                rects.append(tuple(cv2.boundingRect(contour)))  # type: ignore[arg-type]

        if not rects:
            return image, {
                "method": "contour",
                "regions_detected": 0,
                "crop_performed": False,
                "reason": "no_regions",
            }

        merged = self._merge_rects(rects, merge_overlap)
        final_rect = self._merge_all(merged)

        x, y, bw, bh = final_rect
        coverage = (bw * bh) / (image.shape[0] * image.shape[1])
        if coverage > 0.95:
            logger.debug("Detected region covers >95% of image, skipping crop")
            return image, {
                "method": "contour",
                "regions_detected": len(rects),
                "regions_merged": 1,
                "crop_performed": False,
                "reason": "coverage_too_large",
                "coverage": round(coverage, 3),
            }

        x_padded = max(0, x - padding)
        y_padded = max(0, y - padding)
        x2_padded = min(image.shape[1], x + bw + padding)
        y2_padded = min(image.shape[0], y + bh + padding)

        cropped = image[y_padded:y2_padded, x_padded:x2_padded]
        return cropped, {
            "method": "contour",
            "regions_detected": len(rects),
            "regions_merged": 1,
            "bounding_box": {
                "x": x_padded,
                "y": y_padded,
                "w": x2_padded - x_padded,
                "h": y2_padded - y_padded,
            },
            "crop_performed": True,
            "coverage": round(coverage, 3),
        }

    def _merge_rects(self, rects: list[tuple[int, int, int, int]], iou_threshold: float) -> list[tuple[int, int, int, int]]:
        if len(rects) <= 1:
            return rects

        merged = list(rects)
        changed = True
        while changed:
            changed = False
            new_merged = []
            used = [False] * len(merged)
            for i in range(len(merged)):
                if used[i]:
                    continue
                for j in range(i + 1, len(merged)):
                    if used[j]:
                        continue
                    if self._compute_iou(merged[i], merged[j]) > iou_threshold:
                        new_merged.append(self._union_rect(merged[i], merged[j]))
                        used[i] = used[j] = True
                        changed = True
                        break
                if not used[i]:
                    new_merged.append(merged[i])
            merged = new_merged

        return merged

    def _merge_all(self, rects: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
        if not rects:
            return (0, 0, 0, 0)
        x = min(r[0] for r in rects)
        y = min(r[1] for r in rects)
        x2 = max(r[0] + r[2] for r in rects)
        y2 = max(r[1] + r[3] for r in rects)
        return (x, y, x2 - x, y2 - y)

    @staticmethod
    def _compute_iou(r1: tuple[int, int, int, int], r2: tuple[int, int, int, int]) -> float:
        x1 = max(r1[0], r2[0])
        y1 = max(r1[1], r2[1])
        x2 = min(r1[0] + r1[2], r2[0] + r2[2])
        y2 = min(r1[1] + r1[3], r2[1] + r2[3])

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = r1[2] * r1[3]
        area2 = r2[2] * r2[3]
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _union_rect(r1: tuple[int, int, int, int], r2: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        x = min(r1[0], r2[0])
        y = min(r1[1], r2[1])
        x2 = max(r1[0] + r1[2], r2[0] + r2[2])
        y2 = max(r1[1] + r1[3], r2[1] + r2[3])
        return (x, y, x2 - x, y2 - y)
