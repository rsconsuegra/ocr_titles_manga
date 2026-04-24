# US-P7: Notebook & Tests

**Phase**: P (Preprocessing) — Sub-phase PG  
**Priority**: High  
**Status**: Planned

---

## Story

> As an operator, I want a Jupyter notebook to interactively explore preprocessing effects and a complete test suite so that I can visually verify preprocessing quality and have confidence in automated tests.

---

## Scope

### In Scope
- `notebooks/02_preprocessing.ipynb` with visual exploration sections
- Complete test coverage for all preprocessing components in `tests/test_preprocess.py`
- Coverage target >= 80% for `manga_ocr/preprocess/` package

### Out of Scope
- Performance benchmarks
- Integration tests with real manga images (manual via notebook)
- CI pipeline

---

## Preconditions

1. **US-P1 through US-P6 complete**: All preprocessing components implemented and engine integrated
2. Phase 0 test infrastructure in place (`conftest.py`, pytest config)

---

## Implementation Details

### File: `notebooks/02_preprocessing.ipynb`

**Section 1: Setup & Config**
```python
from manga_ocr.config import load_config, load_preprocess_config
from manga_ocr.preprocess import PreProcessingPipeline
import matplotlib.pyplot as plt
import cv2
import numpy as np

config = load_config()
pp_config = load_preprocess_config()
pipeline = PreProcessingPipeline(pp_config, config.images_path)
```

**Section 2: Load & Display Original Image**
```python
image_path = "/Users/rconsuegra/Pictures/images/FB_IMG_1774183131181.jpg"
img = cv2.imread(image_path)
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
plt.imshow(img_rgb)
plt.title("Original Image")
plt.axis('off')
plt.show()
```

**Section 3: Individual Step Exploration**
```python
# Grayscale
from manga_ocr.preprocess.steps.grayscale import GrayscaleStep
gray_step = GrayscaleStep()
gray_img, meta = gray_step.process(img, {})
plt.imshow(gray_img, cmap='gray')
plt.title(f"Grayscale: {meta}")
plt.axis('off')
plt.show()

# Binarize (on grayscale result)
from manga_ocr.preprocess.steps.binarize import BinarizeStep
bin_step = BinarizeStep()
for method in ["otsu", "adaptive_gaussian", "adaptive_mean"]:
    binary, meta = bin_step.process(gray_img, {"method": method})
    plt.imshow(binary, cmap='gray')
    plt.title(f"Binarize ({method}): threshold={meta.get('threshold', 'N/A')}")
    plt.axis('off')
    plt.show()
```

**Section 4: Upscaling Comparison**
```python
from manga_ocr.preprocess.steps.upscale import UpscaleStep
up_step = UpscaleStep()
for method in ["cubic"]:  # add "fsrcnn", "edsr" if models downloaded
    result, meta = up_step.process(gray_img, {"method": method, "scale_factor": 2})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    ax1.imshow(gray_img, cmap='gray')
    ax1.set_title(f"Original {meta['input_size']}")
    ax2.imshow(result, cmap='gray')
    ax2.set_title(f"Upscaled ({method}) {meta['output_size']}")
    plt.show()
```

**Section 5: Full Pipeline Before/After**
```python
result = pipeline.process(image_path)
print(f"Steps: {len(result.steps)}")
for step in result.steps:
    print(f"  {step.step_name}: enabled={step.enabled}, success={step.success}, time={step.processing_time_ms}ms")

# Display original vs preprocessed
if result.output_path:
    pp_img = cv2.imread(result.output_path)
    pp_img_rgb = cv2.cvtColor(pp_img, cv2.COLOR_BGR2RGB)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    ax1.imshow(img_rgb)
    ax1.set_title("Original")
    ax2.imshow(pp_img_rgb)
    ax2.set_title("Preprocessed")
    plt.show()
```

**Section 6: OCR Comparison (with/without preprocessing)**
```python
from manga_ocr.engine import OCREngine
from manga_ocr.config import load_config, load_ocr_config, load_preprocess_config

config = load_config()
ocr_config = load_ocr_config()

# Without preprocessing
engine_no_pp = OCREngine(config, ocr_config)
result_no_pp = engine_no_pp.process(image_path)

# With preprocessing
pp_config = load_preprocess_config()
engine_with_pp = OCREngine(config, ocr_config, pp_config)
result_with_pp = engine_with_pp.process(image_path)

print("=== Without Preprocessing ===")
print(f"Extracted: {result_no_pp.extracted}")
print()
print("=== With Preprocessing ===")
print(f"Extracted: {result_with_pp.extracted}")
if result_with_pp.preprocess_result:
    for step in result_with_pp.preprocess_result.steps:
        print(f"  {step.step_name}: {step.processing_time_ms}ms")
```

### File: `tests/test_preprocess.py`

Comprehensive test suite. Organized by component:

```python
# === Config Tests ===
class TestPreProcessConfig:
    test_load_preprocess_config_valid
    test_load_preprocess_config_missing_file
    test_load_preprocess_config_empty_file
    test_load_preprocess_config_missing_preprocessing_key

# === Schema Tests ===
class TestPreProcessSchemas:
    test_preprocess_step_result_valid
    test_preprocess_result_with_steps
    test_pipeline_result_with_preprocess_result

# === Base Class Tests ===
class TestBasePreProcessor:
    test_base_preprocessor_is_abstract

# === Grayscale Tests ===
class TestGrayscaleStep:
    test_grayscale_3channel
    test_grayscale_4channel
    test_grayscale_already_gray
    test_grayscale_metadata_converted
    test_grayscale_metadata_passthrough
    test_grayscale_always_available

# === Binarize Tests ===
class TestBinarizeStep:
    test_binarize_otsu
    test_binarize_adaptive_gaussian
    test_binarize_adaptive_mean
    test_binarize_invert
    test_binarize_color_input_auto_converts
    test_binarize_invalid_method_raises
    test_binarize_even_block_size_corrected
    test_binarize_small_block_size_corrected
    test_binarize_always_available

# === Upscale Tests ===
class TestUpscaleStep:
    test_upscale_cubic_doubles_size
    test_upscale_cubic_3channel
    test_upscale_cubic_grayscale
    test_upscale_skip_scale_1
    test_upscale_unknown_method_fallback
    test_upscale_realesrgan_fallback
    test_upscale_fsrcnn_model_cached
    test_upscale_metadata

# === Denoise Tests ===
class TestDenoiseStep:
    test_denoise_gaussian_light
    test_denoise_gaussian_medium
    test_denoise_gaussian_heavy
    test_denoise_median_light
    test_denoise_nlmeans_grayscale
    test_denoise_nlmeans_color
    test_denoise_invalid_method_fallback
    test_denoise_invalid_strength_fallback
    test_denoise_preserves_dimensions
    test_denoise_metadata
    test_denoise_always_available

# === ROI Tests ===
class TestROIStep:
    test_roi_contour_detects_text
    test_roi_no_regions
    test_roi_small_image_skip
    test_roi_large_coverage_skip
    test_roi_padding_applied
    test_roi_padding_clamped
    test_roi_merge_overlapping
    test_roi_grayscale_input
    test_roi_color_input
    test_roi_metadata_structure
    test_roi_always_available
    test_roi_unknown_method

# === Pipeline Tests ===
class TestPreProcessingPipeline:
    test_pipeline_init_with_steps
    test_pipeline_process_returns_result
    test_pipeline_process_invalid_image
    test_pipeline_debug_saves_intermediates
    test_pipeline_disabled_step_skipped
    test_pipeline_step_execution_order
    test_pipeline_step_failure_continues

# === Engine Integration Tests ===
class TestEnginePreprocessing:
    test_process_with_preprocessing_enabled
    test_process_with_preprocessing_disabled
    test_process_preprocessing_failure_fallback
    test_process_preprocessing_provides_image_to_ocr
    test_process_preprocessing_result_in_pipeline_result
```

---

## Postconditions

1. `notebooks/02_preprocessing.ipynb` runnable end-to-end with sample images
2. `make test` passes with all preprocessing tests + all existing Phase 0 tests
3. `make lint` passes with no errors
4. Coverage for `manga_ocr/preprocess/` package >= 80%
5. Total test count increased by ~50+ tests from preprocessing
6. No test requires real API calls, real model weights, or specific images

---

## Validation Checklist

- [ ] `make test` runs all tests and exits 0
- [ ] `make lint` passes with no errors
- [ ] `tests/test_preprocess.py` covers all preprocessing components
- [ ] No test makes real API calls or downloads models (all mocked)
- [ ] Coverage for `manga_ocr/preprocess/` >= 80%
- [ ] All existing Phase 0 tests still pass
- [ ] Notebook runs without errors on sample images
- [ ] Notebook displays before/after comparison visually

---

## Test Plan

This IS the test plan — meta-story. Verify by running:

```bash
make test
make lint
uv run pytest tests/ --cov=manga_ocr/preprocess --cov-report=term-missing
```

All must pass with >= 80% coverage on `manga_ocr/preprocess/`.

---

## Questions for Operator

None.

---

## Dependencies

- **US-P1 through US-P6** all complete

---

## Estimated Complexity

**Medium** — individual tests are straightforward, but there are many across all components. The notebook requires sample images to be available.
