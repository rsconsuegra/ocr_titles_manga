# US-P5: ROI Detection

**Phase**: P (Preprocessing) — Sub-phase PE  
**Priority**: Medium  
**Status**: Planned

---

## Story

> As an operator, I want the preprocessing pipeline to detect and crop text-containing regions from social media screenshots so that OCR models focus on relevant text areas instead of full-screen noise.

---

## Scope

### In Scope
- Contour-based text region detection
- Configurable minimum contour area, padding, merge overlap
- Single merged crop output
- Small image detection (skip ROI)
- Large coverage detection (skip crop if contour covers > 95% of image)

### Out of Scope
- EAST text detection model (future)
- Multi-region output (separate crops per region)
- Rotation / perspective correction

---

## Preconditions

1. **US-P1 complete**: Base infrastructure working
2. `opencv-python-headless` and `numpy` available

---

## Implementation Details

### File: `manga_ocr/preprocess/steps/roi.py`

```python
import logging

import cv2
import numpy as np

from manga_ocr.preprocess.base import BasePreProcessor

logger = logging.getLogger(__name__)


class ROIStep(BasePreProcessor):

    @property
    def name(self) -> str:
        return "roi"

    @property
    def is_available(self) -> bool:
        return True

    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        method = config.get("method", "contour")

        h, w = image.shape[:2]
        if h < 100 or w < 100:
            logger.debug("Image too small for ROI detection, skipping")
            return image, {"method": method, "regions_detected": 0, "crop_performed": False, "reason": "image_too_small"}

        if method == "contour":
            return self._contour_detect(image, config)
        else:
            logger.warning(f"Unknown ROI method '{method}', no crop performed")
            return image, {"method": method, "regions_detected": 0, "crop_performed": False, "reason": "unknown_method"}

    def _contour_detect(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        min_area = config.get("min_area", 500)
        padding = config.get("padding", 10)
        merge_overlap = config.get("merge_overlap", 0.3)

        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= min_area:
                rects.append(cv2.boundingRect(contour))

        if not rects:
            return image, {"method": "contour", "regions_detected": 0, "crop_performed": False, "reason": "no_regions"}

        merged = self._merge_rects(rects, merge_overlap)
        merged = self._merge_all(merged)

        x, y, bw, bh = merged
        x = max(0, x - padding)
        y = max(0, y - padding)
        x2 = min(image.shape[1], x + bw + 2 * padding)
        y2 = min(image.shape[0], y + bh + 2 * padding)

        coverage = (bw * bh) / (image.shape[0] * image.shape[1])
        if coverage > 0.95:
            logger.debug("Detected region covers >95%% of image, skipping crop")
            return image, {
                "method": "contour",
                "regions_detected": len(rects),
                "regions_merged": 1,
                "crop_performed": False,
                "reason": "coverage_too_large",
                "coverage": round(coverage, 3),
            }

        cropped = image[y:y2, x:x2]
        return cropped, {
            "method": "contour",
            "regions_detected": len(rects),
            "regions_merged": 1,
            "bounding_box": {"x": x, "y": y, "w": x2 - x, "h": y2 - y},
            "crop_performed": True,
            "coverage": round(coverage, 3),
        }

    def _merge_rects(self, rects: list[tuple], iou_threshold: float) -> list[tuple]:
        """Merge overlapping rectangles based on IoU threshold."""
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

    def _merge_all(self, rects: list[tuple]) -> tuple[int, int, int, int]:
        """Merge all rects into single bounding box."""
        if not rects:
            return (0, 0, 0, 0)
        x = min(r[0] for r in rects)
        y = min(r[1] for r in rects)
        x2 = max(r[0] + r[2] for r in rects)
        y2 = max(r[1] + r[3] for r in rects)
        return (x, y, x2 - x, y2 - y)

    @staticmethod
    def _compute_iou(r1: tuple, r2: tuple) -> float:
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
    def _union_rect(r1: tuple, r2: tuple) -> tuple:
        x = min(r1[0], r2[0])
        y = min(r1[1], r2[1])
        x2 = max(r1[0] + r1[2], r2[0] + r2[2])
        y2 = max(r1[1] + r1[3], r2[1] + r2[3])
        return (x, y, x2 - x, y2 - y)
```

### File: `manga_ocr/preprocess/pipeline.py` (updated)

Add `"roi"` to `_create_step()` mapping.

---

## Postconditions

1. `ROIStep` with `method="contour"` detects text regions via contour analysis
2. Returns cropped image when regions detected
3. Returns original image when no regions detected
4. Returns original image when detected coverage > 95%
5. Returns original image for images < 100x100
6. Padding applied around detected regions (clamped to image bounds)
7. Multiple overlapping regions merged via IoU threshold
8. Final output is single merged crop
9. Metadata includes regions_detected, bounding_box, crop_performed

---

## Validation Checklist

- [ ] Contour detection finds text regions in test image with text
- [ ] No regions detected returns original image with metadata
- [ ] Small image (< 100x100) returns original with metadata
- [ ] Coverage > 95% returns original with metadata
- [ ] Padding applied and clamped to image bounds
- [ ] IoU-based merging combines overlapping rects
- [ ] Final merge produces single bounding box
- [ ] Metadata has regions_detected, bounding_box, crop_performed
- [ ] Works with both grayscale and color input

---

## Test Plan

### File: `tests/test_preprocess.py` (updated)

1. `test_roi_contour_detects_text` — create image with white rect on black bg, assert crop
2. `test_roi_no_regions` — blank image, assert original returned, `regions_detected=0`
3. `test_roi_small_image_skip` — 50x50 image, assert original returned
4. `test_roi_large_coverage_skip` — image where contour covers > 95%, assert original returned
5. `test_roi_padding_applied` — verify crop is larger than detected region by padding amount
6. `test_roi_padding_clamped` — region at edge of image, assert no negative coords
7. `test_roi_merge_overlapping` — two overlapping rects, assert merged into one
8. `test_roi_grayscale_input` — 2D array input, assert works
9. `test_roi_color_input` — 3-channel input, assert works
10. `test_roi_metadata_structure` — assert metadata has all expected keys
11. `test_roi_always_available` — assert `is_available` is True
12. `test_roi_unknown_method` — method="east", assert no crop

Test fixtures:

```python
@pytest.fixture
def text_like_image():
    """200x200 black image with white rectangle (simulating text region)."""
    img = np.zeros((200, 200), dtype=np.uint8)
    img[50:150, 30:170] = 255  # white region
    return img
```

---

## Questions for Operator

None.

---

## Dependencies

- **US-P1** complete

---

## Estimated Complexity

**Medium** — contour detection is standard OpenCV, but the merging logic, padding clamping, and edge cases (small image, large coverage) add moderate complexity.
