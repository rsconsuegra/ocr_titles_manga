# Phase P: Image Preprocessing Pipeline

**Status**: Planned
**Prerequisite**: Phase 0 (OCR Engine) complete
**Delivers**: Configurable image preprocessing pipeline that improves OCR accuracy by detecting text regions, converting to grayscale, upscaling, denoising, and binarizing before OCR models run

---

## Scope

A preprocessing pipeline module (`manga_ocr/preprocess/`) that runs before OCR models. Configurable via `preprocess.yaml`, supports debug mode with intermediate image saves, and integrates seamlessly into the existing `OCREngine.process()` flow.

### Problem Statement

Social media screenshots contain manga title text in various conditions: low resolution, color backgrounds, noise, mixed orientations. OCR accuracy degrades significantly without preprocessing. This pipeline normalizes image quality to maximize OCR model performance.

---

## Sub-Phases

### PA — Foundation (Config, Schemas, Base Infrastructure)

**Capabilities**:
- Load and validate `preprocess.yaml` configuration
- Pydantic schemas for preprocessing results
- Abstract base class `BasePreProcessor` defining the contract
- `PreProcessingPipeline` orchestrator skeleton
- Debug mode: save intermediate images to disk

**Data Models** (Pydantic v2):

```
PreProcessStepResult:
  step_name: str
  enabled: bool
  success: bool
  processing_time_ms: int
  output_path: str | None
  error: str | None = None
  metadata: dict[str, Any] = {}

PreProcessResult:
  input_path: str
  output_path: str | None         # final preprocessed image path (or None if disabled)
  steps: list[PreProcessStepResult]
  total_processing_time_ms: int

PipelineResult (updated):
  ...existing fields...
  preprocess_result: PreProcessResult | None = None
```

**Config File Format** (`preprocess.yaml`):

```yaml
preprocessing:
  enabled: true
  debug: true
  roi:
    enabled: true
    method: "contour"           # contour | east (future)
    min_area: 500
    padding: 10
    merge_overlap: 0.3
  grayscale:
    enabled: true
  upscale:
    enabled: true
    method: "cubic"             # cubic | fsrcnn | edsr | realesrgan
    scale_factor: 2
  denoise:
    enabled: true
    method: "gaussian"          # gaussian | median | nlmeans
    strength: "light"           # light | medium | heavy
  binarize:
    enabled: true
    method: "otsu"              # otsu | adaptive_gaussian | adaptive_mean
    invert: false
    block_size: 11
    c: 2
```

**Base PreProcessor Interface** (`manga_ocr/preprocess/base.py`):

```python
class BasePreProcessor(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]: ...
```

- `process()` returns `(processed_image, metadata_dict)`
- `metadata_dict` contains step-specific info (e.g., `{"scale_factor": 2}`, `{"regions_detected": 1}`)
- When step is disabled: return input image unchanged with empty metadata

**Pipeline Orchestrator** (`manga_ocr/preprocess/pipeline.py`):

```python
class PreProcessingPipeline:
    STEP_ORDER = ["roi", "grayscale", "upscale", "denoise", "binarize"]

    def __init__(self, config: dict, images_path: Path): ...

    def process(self, image_path: str) -> PreProcessResult: ...
```

- Fixed step order: ROI -> Grayscale -> Upscale -> Denoise -> Binarize
- Each step checks its `enabled` flag; disabled steps pass-through
- Debug mode: saves intermediate image after each step to `{images_path}/.preprocess/{timestamp}_{step_name}.png`
- Creates `.preprocess/` directory on first use

**Config Loader** (`manga_ocr/config.py` updated):

```python
def load_preprocess_config(config_path: str | Path = "preprocess.yaml") -> dict: ...
```

**Files**:
- `manga_ocr/preprocess/__init__.py`
- `manga_ocr/preprocess/base.py`
- `manga_ocr/preprocess/pipeline.py`
- `manga_ocr/schemas.py` (updated: add PreProcessStepResult, PreProcessResult, update PipelineResult)
- `manga_ocr/config.py` (updated: add load_preprocess_config)
- `preprocess.yaml`
- `tests/test_preprocess.py`

---

### PB — Grayscale + Binarization

**Capabilities**:
- Grayscale conversion: standard OpenCV BGR-to-gray
- Binarization: Otsu, Adaptive Gaussian, Adaptive Mean methods

**Grayscale Step** (`manga_ocr/preprocess/steps/grayscale.py`):

```python
class GrayscaleStep(BasePreProcessor):
    name = "grayscale"

    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        # cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if 3-channel
        # Already grayscale: pass through
        # Return (grayscale_image, {"input_channels": ..., "output_channels": 1})
```

- If image is already grayscale (2D array): pass through
- If image is BGRA (4-channel): convert to BGR first, then grayscale
- Metadata: `{"original_channels": 3, "converted": true}`

**Binarization Step** (`manga_ocr/preprocess/steps/binarize.py`):

```python
class BinarizeStep(BasePreProcessor):
    name = "binarize"

    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        method = config.get("method", "otsu")
        # otsu: cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # adaptive_gaussian: cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, ...)
        # adaptive_mean: cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_MEAN_C, ...)
        # invert: use THRESH_BINARY_INV instead of THRESH_BINARY
```

- Input must be grayscale (2D array); if not, convert first
- Otsu: automatic threshold calculation, ignores manual threshold
- Adaptive methods: use `block_size` (must be odd, >= 3) and `c` (constant subtracted from mean)
- `invert`: swaps foreground/background (useful for dark-on-light vs light-on-dark)
- Metadata: `{"method": "otsu", "threshold": 127.5, "invert": false}`
- Error handling: invalid method raises `ValueError`, invalid block_size auto-corrected to nearest odd >= 3

**Files**:
- `manga_ocr/preprocess/steps/__init__.py`
- `manga_ocr/preprocess/steps/grayscale.py`
- `manga_ocr/preprocess/steps/binarize.py`
- `tests/test_preprocess.py` (updated)

---

### PC — Upscaling

**Capabilities**:
- Cubic interpolation (fast, no model download)
- FSRCNN super-resolution (small model, fast inference)
- EDSR super-resolution (larger model, better quality)
- Real-ESRGAN super-resolution (best quality, requires separate package)

**Upscale Step** (`manga_ocr/preprocess/steps/upscale.py`):

```python
class UpscaleStep(BasePreProcessor):
    name = "upscale"

    @property
    def is_available(self) -> bool:
        # cubic: always available (OpenCV)
        # fsrcnn/edsr: available if cv2.dnn is available + model file exists
        # realesrgan: available if realesrgan package is installed

    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        method = config.get("method", "cubic")
        scale_factor = config.get("scale_factor", 2)
        # cubic: cv2.resize(image, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
        # fsrcnn: cv2.dnn_superres.DnnSuperResImpl_create() + readModel + upsample
        # edsr: same API as fsrcnn but different model file
        # realesrgan: from realesrgan import RealESRGANer + upscale
```

**Method Details**:

| Method | Quality | Speed | Model Size | Dependencies |
|--------|---------|-------|------------|--------------|
| cubic | Low | Very fast | None | opencv only |
| fsrcnn | Medium | Fast (~50ms) | ~4KB | opencv + model file |
| edsr | High | Slow (~200ms) | ~40MB | opencv + model file |
| realesrgan | Best | Slowest (~500ms) | ~65MB | realesrgan package |

**Model File Management**:
- FSRCNN/EDSR models downloaded from OpenCV repo on first use
- Stored in `~/.manga_ocr/models/` directory
- Auto-create directory if not exists
- Model filenames: `FSRCNN_x{scale}.pb`, `EDSR_x{scale}.pb`
- Download URLs: OpenCV super-resolution models repository
- `is_available` checks: model file exists on disk

**Real-ESRGAN**:
- Requires `realesrgan` pip package (optional dependency)
- `is_available` checks: package importable + model weights exist
- Not installed by default; user must opt in
- Fallback: if realesrgan selected but unavailable, log warning and use cubic instead

**Files**:
- `manga_ocr/preprocess/steps/upscale.py`
- `tests/test_preprocess.py` (updated)

---

### PD — Denoising

**Capabilities**:
- Gaussian blur: fast, configurable kernel size
- Median filter: good for salt-and-pepper noise
- Non-local means (NLMeans): best quality, slowest

**Denoise Step** (`manga_ocr/preprocess/steps/denoise.py`):

```python
class DenoiseStep(BasePreProcessor):
    name = "denoise"

    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        method = config.get("method", "gaussian")
        strength = config.get("strength", "light")
        # gaussian: cv2.GaussianBlur(image, kernel_size, sigma)
        # median: cv2.medianBlur(image, kernel_size)
        # nlmeans: cv2.fastNlMeansDenoising(image, h, ...) or cv2.fastNlMeansDenoisingColored(...)
```

**Strength Presets**:

| Strength | Gaussian kernel | Median kernel | NLMeans h |
|----------|----------------|---------------|-----------|
| light | 3x3, sigma=0.5 | 3 | h=3 |
| medium | 5x5, sigma=1.0 | 5 | h=6 |
| heavy | 7x7, sigma=1.5 | 7 | h=10 |

- NLMeans: use `fastNlMeansDenoising()` for grayscale, `fastNlMeansDenoisingColored()` for color
- Metadata: `{"method": "gaussian", "strength": "light", "kernel_size": 3}`
- Error handling: invalid method raises `ValueError`, invalid strength defaults to "light" with warning

**Files**:
- `manga_ocr/preprocess/steps/denoise.py`
- `tests/test_preprocess.py` (updated)

---

### PE — ROI Detection

**Capabilities**:
- Detect text-containing regions in social media screenshots
- Crop to detected region(s) to reduce noise from non-text areas
- Contour-based detection (fast, no model required)
- Single merged crop output (multi-region deferred to Phase 2)

**ROI Step** (`manga_ocr/preprocess/steps/roi.py`):

```python
class ROIStep(BasePreProcessor):
    name = "roi"

    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        method = config.get("method", "contour")
        # contour: grayscale -> threshold -> find contours -> filter by area -> merge overlapping -> crop
        # east: future implementation (requires model download)
```

**Contour-Based Detection Flow**:
1. Convert to grayscale
2. Apply Gaussian blur (3x3) to smooth
3. Adaptive threshold to get binary image
4. Find contours with `cv2.findContours()`
5. Filter contours by `min_area` (default 500px²)
6. Compute bounding rectangles for each contour
7. Merge overlapping rectangles (IoU threshold = `merge_overlap`, default 0.3)
8. Add padding (default 10px) to merged regions
9. If multiple regions: merge all into single bounding box
10. Crop image to merged region
11. If no regions detected: return original image with `metadata["regions_detected"] = 0`

**Configuration Parameters**:
- `method`: `"contour"` (only option in Phase P)
- `min_area`: minimum contour area in pixels² (default 500)
- `padding`: pixels to add around detected region (default 10)
- `merge_overlap`: IoU threshold for merging adjacent regions (default 0.3)

**Metadata Output**:
```json
{
  "method": "contour",
  "regions_detected": 3,
  "regions_merged": 1,
  "bounding_box": {"x": 50, "y": 100, "w": 400, "h": 200},
  "crop_performed": true
}
```

**Edge Cases**:
- No contours found: return original image, `metadata["regions_detected"] = 0`
- Contour covers > 95% of image: skip crop (likely full-page text), log debug
- Very small image (< 100x100): skip ROI detection entirely
- Image already grayscale: use as-is (no re-conversion)

**Files**:
- `manga_ocr/preprocess/steps/roi.py`
- `tests/test_preprocess.py` (updated)

---

### PF — Engine Integration

**Capabilities**:
- `OCREngine.process()` updated to run preprocessing before OCR
- `PipelineResult` includes `preprocess_result` field
- Preprocessed image fed to OCR models; original path preserved

**Integration Flow** (updated `OCREngine.process()`):

```
1. Validate image_path (exists, supported format)
2. [NEW] Check if preprocessing enabled in config
3. [NEW] If enabled: run PreProcessingPipeline.process(image_path)
4. [NEW] Use preprocessed image path for OCR (or original if disabled/failed)
5. Run all enabled/available OCR models on (possibly preprocessed) image
6. Post-process each successful OCR result (LLM + rules)
7. Select best extraction
8. Return PipelineResult (now includes preprocess_result)
```

**Engine Constructor Update**:

```python
class OCREngine:
    def __init__(self, config: AppConfig, ocr_config: dict, preprocess_config: dict | None = None):
        self._preprocess_pipeline = None
        if preprocess_config and preprocess_config.get("preprocessing", {}).get("enabled", False):
            self._preprocess_pipeline = PreProcessingPipeline(preprocess_config, config.images_path)
```

**Backward Compatibility**:
- `preprocess_config` parameter is optional (default `None`)
- If `None` or preprocessing disabled: no preprocessing, existing behavior unchanged
- All existing tests continue to pass without modification
- `main.py` updated to load `preprocess.yaml` and pass to engine

**Files**:
- `manga_ocr/engine.py` (updated)
- `main.py` (updated)
- `tests/test_engine.py` (updated: add preprocessing integration tests)
- `tests/test_cli.py` (no changes needed)

---

### PG — Notebook & Tests

**Capabilities**:
- Jupyter notebook for interactive preprocessing exploration
- Complete test suite for all preprocessing components

**Notebook** (`notebooks/02_preprocessing.ipynb`):

Sections:
1. Load config and display preprocessing settings
2. Load a sample image and display original
3. Run individual steps with debug output (show intermediates)
4. Run full preprocessing pipeline, display before/after comparison
5. Run full pipeline (preprocessing + OCR) and compare results with/without preprocessing
6. Batch comparison: process multiple images with/without preprocessing, show OCR accuracy difference

**Test Suite** (`tests/test_preprocess.py`):

- All tests use `numpy.ndarray` fixtures (no real image files needed)
- Mock OpenCV calls where appropriate
- Test each step independently
- Test pipeline orchestration
- Test config loading
- Test debug mode intermediate saves
- Test integration with OCREngine

**Test Categories**:
1. Config loading tests (parse preprocess.yaml, validate fields)
2. Schema tests (PreProcessStepResult, PreProcessResult)
3. Grayscale step tests (3-channel, 4-channel, already-gray)
4. Binarize step tests (otsu, adaptive_gaussian, adaptive_mean, invert)
5. Upscale step tests (cubic always available, model-based availability checks)
6. Denoise step tests (gaussian, median, nlmeans, strength presets)
7. ROI step tests (contour detection, no regions, small image, large coverage)
8. Pipeline orchestration tests (step ordering, disabled steps, debug mode)
9. Engine integration tests (preprocessing enabled/disabled, preprocessing failure graceful)

---

## Dependencies

### Required (added to pyproject.toml)
- `opencv-python-headless>=4.8.0`
- `numpy>=1.26.0`

### Optional (user installs manually)
- `realesrgan` (only if upscale method = realesrgan)

### Model Downloads (automatic on first use)
- FSRCNN models: `~/.manga_ocr/models/FSRCNN_x2.pb`, `FSRCNN_x3.pb`, `FSRCNN_x4.pb`
- EDSR models: `~/.manga_ocr/models/EDSR_x2.pb`, `EDSR_x3.pb`, `EDSR_x4.pb`

---

## Phase P Exclusions

- No multi-region ROI output (single merged crop only)
- No EAST text detection model (future)
- No rotation correction / deskewing
- No perspective correction
- No color normalization
- No custom model training
- No GPU acceleration options (CPU only in Phase P)
- No preprocessing in CLI notebook section (separate notebook)

---

## User Story Numbering

| Story | Name | Sub-phase |
|-------|------|-----------|
| US-P1 | Config, Schemas & Base Infrastructure | PA |
| US-P2 | Grayscale + Binarization | PB |
| US-P3 | Upscaling | PC |
| US-P4 | Denoising | PD |
| US-P5 | ROI Detection | PE |
| US-P6 | Engine Integration | PF |
| US-P7 | Notebook & Tests | PG |

---

## Implementation Order

```
US-P1 (Foundation)
    |
    +-> US-P2 (Grayscale + Binarize)
    |       |
    |       +-> US-P3 (Upscale)
    |       |       |
    |       |       +-> US-P4 (Denoise)
    |       |
    |       +-> US-P5 (ROI)
    |
    +-> US-P6 (Engine Integration) -- depends on all steps
            |
            +-> US-P7 (Notebook + Tests) -- depends on integration
```

US-P2, US-P3, US-P4, US-P5 can be implemented in parallel after US-P1. US-P6 requires all steps. US-P7 requires US-P6.
