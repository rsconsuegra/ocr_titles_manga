# US-P2: Grayscale + Binarization

**Phase**: P (Preprocessing) — Sub-phase PB  
**Priority**: High  
**Status**: Planned

---

## Story

> As an operator, I want the preprocessing pipeline to convert images to grayscale and apply binarization so that OCR models receive high-contrast black-and-white text images for better accuracy.

---

## Scope

### In Scope
- Grayscale conversion step (BGR/RGBA → grayscale)
- Binarization step (Otsu, Adaptive Gaussian, Adaptive Mean)
- Invert option for binarization
- Register steps in pipeline

### Out of Scope
- Other preprocessing steps (US-P3, US-P4, US-P5)
- Engine integration (US-P6)
- Notebook (US-P7)

---

## Preconditions

1. **US-P1 complete**: `BasePreProcessor`, `PreProcessingPipeline`, schemas, config loading all working
2. `opencv-python-headless` and `numpy` available

---

## Implementation Details

### File: `manga_ocr/preprocess/steps/grayscale.py`

```python
import numpy as np
import cv2

from manga_ocr.preprocess.base import BasePreProcessor


class GrayscaleStep(BasePreProcessor):

    @property
    def name(self) -> str:
        return "grayscale"

    @property
    def is_available(self) -> bool:
        return True  # Always available (pure OpenCV)

    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        if image.ndim == 2:
            return image, {"original_channels": 1, "converted": False}

        channels = image.shape[2] if image.ndim == 3 else 1

        if channels == 4:
            bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        elif channels == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        return gray, {"original_channels": channels, "converted": True}
```

### File: `manga_ocr/preprocess/steps/binarize.py`

```python
import numpy as np
import cv2

from manga_ocr.preprocess.base import BasePreProcessor


class BinarizeStep(BasePreProcessor):

    @property
    def name(self) -> str:
        return "binarize"

    @property
    def is_available(self) -> bool:
        return True  # Always available (pure OpenCV)

    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        method = config.get("method", "otsu")
        invert = config.get("invert", False)

        if image.ndim == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        thresh_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY

        if method == "otsu":
            threshold, binary = cv2.threshold(image, 0, 255, thresh_type + cv2.THRESH_OTSU)
            return binary, {"method": "otsu", "threshold": float(threshold), "invert": invert}

        block_size = config.get("block_size", 11)
        c = config.get("c", 2)

        if block_size < 3:
            block_size = 3
        if block_size % 2 == 0:
            block_size += 1

        if method == "adaptive_gaussian":
            binary = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, thresh_type, block_size, c)
        elif method == "adaptive_mean":
            binary = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_MEAN_C, thresh_type, block_size, c)
        else:
            raise ValueError(f"Unknown binarization method: {method}")

        return binary, {"method": method, "block_size": block_size, "c": c, "invert": invert}
```

### File: `manga_ocr/preprocess/pipeline.py` (updated)

Update `_create_step()` to register grayscale and binarize:

```python
def _create_step(self, name: str, config: dict) -> BasePreProcessor | None:
    from manga_ocr.preprocess.steps.grayscale import GrayscaleStep
    from manga_ocr.preprocess.steps.binarize import BinarizeStep

    steps_map = {
        "grayscale": GrayscaleStep,
        "binarize": BinarizeStep,
    }

    step_cls = steps_map.get(name)
    if step_cls is not None:
        step = step_cls()
        if step.is_available:
            return step
        logger.warning(f"Preprocessing step '{name}' not available")
    return None
```

---

## Postconditions

1. `GrayscaleStep` converts 3-channel BGR images to grayscale
2. `GrayscaleStep` converts 4-channel BGRA images to grayscale
3. `GrayscaleStep` passes through already-grayscale images unchanged
4. `BinarizeStep` with `method="otsu"` applies Otsu's thresholding
5. `BinarizeStep` with `method="adaptive_gaussian"` applies adaptive Gaussian thresholding
6. `BinarizeStep` with `method="adaptive_mean"` applies adaptive mean thresholding
7. `BinarizeStep` with `invert=true` inverts the binary output
8. `BinarizeStep` auto-converts color images to grayscale before binarizing
9. Both steps registered in pipeline and run in correct order (grayscale before binarize)
10. Invalid binarization method raises `ValueError`

---

## Validation Checklist

- [ ] `GrayscaleStep` converts 3-channel image to 2D grayscale
- [ ] `GrayscaleStep` converts 4-channel image to 2D grayscale
- [ ] `GrayscaleStep` passes through 2D grayscale image unchanged
- [ ] `GrayscaleStep` returns metadata with `original_channels` and `converted`
- [ ] `BinarizeStep` with otsu produces binary image
- [ ] `BinarizeStep` with adaptive_gaussian produces binary image
- [ ] `BinarizeStep` with adaptive_mean produces binary image
- [ ] `BinarizeStep` with invert=true produces inverted binary
- [ ] `BinarizeStep` with invalid method raises ValueError
- [ ] `BinarizeStep` auto-converts color input to grayscale
- [ ] `BinarizeStep` corrects even block_size to odd
- [ ] Pipeline runs grayscale then binarize in order
- [ ] Both steps report correct processing time

---

## Test Plan

### File: `tests/test_preprocess.py` (updated)

**Grayscale tests**:
1. `test_grayscale_3channel` — create BGR numpy array, assert output is 2D
2. `test_grayscale_4channel` — create BGRA numpy array, assert output is 2D
3. `test_grayscale_already_gray` — pass 2D array, assert unchanged
4. `test_grayscale_metadata_converted` — assert metadata has `converted=True` for 3-channel input
5. `test_grayscale_metadata_passthrough` — assert metadata has `converted=False` for 2D input
6. `test_grayscale_always_available` — assert `is_available` is True

**Binarize tests**:
7. `test_binarize_otsu` — create grayscale array, assert binary output (all values 0 or 255)
8. `test_binarize_adaptive_gaussian` — assert binary output
9. `test_binarize_adaptive_mean` — assert binary output
10. `test_binarize_invert` — compare otsu normal vs inverted, assert they are bitwise complements
11. `test_binarize_color_input_auto_converts` — pass 3-channel array, assert no error
12. `test_binarize_invalid_method_raises` — pass method="unknown", assert ValueError
13. `test_binarize_even_block_size_corrected` — pass block_size=10, assert works (corrected to 11)
14. `test_binarize_small_block_size_corrected` — pass block_size=1, assert works (corrected to 3)
15. `test_binarize_always_available` — assert `is_available` is True

**Pipeline integration tests**:
16. `test_pipeline_grayscale_then_binarize` — mock pipeline with both steps, verify execution order
17. `test_pipeline_binarize_without_grayscale` — binarize handles color input independently

Use `numpy` arrays as test fixtures:

```python
@pytest.fixture
def bgr_image():
    return np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

@pytest.fixture
def gray_image():
    return np.random.randint(0, 255, (100, 100), dtype=np.uint8)
```

---

## Questions for Operator

None.

---

## Dependencies

- **US-P1** complete (base class, pipeline skeleton, schemas)

---

## Estimated Complexity

**Low-Medium** — OpenCV calls are straightforward, but edge cases (4-channel, auto-convert, block_size correction) add moderate complexity.
