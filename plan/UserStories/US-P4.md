# US-P4: Denoising

**Phase**: P (Preprocessing) — Sub-phase PD  
**Priority**: High  
**Status**: Planned

---

## Story

> As an operator, I want the preprocessing pipeline to remove image noise so that OCR models see cleaner text with fewer artifacts.

---

## Scope

### In Scope
- Gaussian blur denoising (configurable strength)
- Median filter denoising (configurable strength)
- Non-local means (NLMeans) denoising (configurable strength)
- Strength presets: light, medium, heavy
- Color-aware NLMeans (uses `fastNlMeansDenoisingColored` for color images)

### Out of Scope
- Other preprocessing steps
- Custom kernel sizes beyond presets

---

## Preconditions

1. **US-P1 complete**: Base infrastructure working
2. `opencv-python-headless` and `numpy` available

---

## Implementation Details

### File: `manga_ocr/preprocess/steps/denoise.py`

```python
import logging

import cv2
import numpy as np

from manga_ocr.preprocess.base import BasePreProcessor

logger = logging.getLogger(__name__)

STRENGTH_PRESETS = {
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

    @property
    def name(self) -> str:
        return "denoise"

    @property
    def is_available(self) -> bool:
        return True

    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        method = config.get("method", "gaussian")
        strength = config.get("strength", "light")

        if method not in STRENGTH_PRESETS:
            logger.warning(f"Unknown denoise method '{method}', defaulting to gaussian")
            method = "gaussian"

        if strength not in STRENGTH_PRESETS[method]:
            logger.warning(f"Unknown strength '{strength}', defaulting to light")
            strength = "light"

        params = STRENGTH_PRESETS[method][strength]

        if method == "gaussian":
            result = cv2.GaussianBlur(image, (params["ksize"], params["ksize"]), params["sigma"])
        elif method == "median":
            result = cv2.medianBlur(image, params["ksize"])
        elif method == "nlmeans":
            if image.ndim == 2:
                result = cv2.fastNlMeansDenoising(image, None, h=params["h"])
            else:
                result = cv2.fastNlMeansDenoisingColored(image, None, h=params["h"])
        else:
            result = image

        return result, {"method": method, "strength": strength, "params": params}
```

### File: `manga_ocr/preprocess/pipeline.py` (updated)

Add `"denoise"` to `_create_step()` mapping.

---

## Postconditions

1. `DenoiseStep` with `method="gaussian"` applies Gaussian blur with strength-appropriate kernel
2. `DenoiseStep` with `method="median"` applies median filter with strength-appropriate kernel
3. `DenoiseStep` with `method="nlmeans"` applies NLMeans denoising (color-aware for 3-channel)
4. Invalid method defaults to `"gaussian"` with warning
5. Invalid strength defaults to `"light"` with warning
6. Step always available (`is_available=True`)
7. Output image has same dimensions as input

---

## Validation Checklist

- [ ] Gaussian light applies 3x3 kernel
- [ ] Gaussian medium applies 5x5 kernel
- [ ] Gaussian heavy applies 7x7 kernel
- [ ] Median light applies ksize=3
- [ ] NLMeans grayscale uses `fastNlMeansDenoising`
- [ ] NLMeans color uses `fastNlMeansDenoisingColored`
- [ ] Invalid method falls back to gaussian
- [ ] Invalid strength falls back to light
- [ ] Output dimensions match input dimensions
- [ ] Metadata includes method, strength, and params

---

## Test Plan

### File: `tests/test_preprocess.py` (updated)

1. `test_denoise_gaussian_light` — verify kernel size 3x3 from metadata
2. `test_denoise_gaussian_medium` — verify kernel size 5x5 from metadata
3. `test_denoise_gaussian_heavy` — verify kernel size 7x7 from metadata
4. `test_denoise_median_light` — verify ksize=3 from metadata
5. `test_denoise_nlmeans_grayscale` — 2D input, assert output shape same
6. `test_denoise_nlmeans_color` — 3-channel input, assert output shape same
7. `test_denoise_invalid_method_fallback` — method="unknown", assert gaussian used
8. `test_denoise_invalid_strength_fallback` — strength="extreme", assert light used
9. `test_denoise_preserves_dimensions` — 100x100 input, assert 100x100 output
10. `test_denoise_metadata` — assert metadata has method, strength, params
11. `test_denoise_always_available` — assert `is_available` is True

---

## Questions for Operator

None.

---

## Dependencies

- **US-P1** complete

---

## Estimated Complexity

**Low** — straightforward OpenCV calls with configurable presets.
