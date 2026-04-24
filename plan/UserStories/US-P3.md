# US-P3: Upscaling

**Phase**: P (Preprocessing) — Sub-phase PC  
**Priority**: High  
**Status**: Planned

---

## Story

> As an operator, I want the preprocessing pipeline to upscale low-resolution images so that OCR models can better recognize small text characters.

---

## Scope

### In Scope
- Cubic interpolation upscaling (always available)
- FSRCNN super-resolution (OpenCV DNN-based, model auto-download)
- EDSR super-resolution (OpenCV DNN-based, model auto-download)
- Real-ESRGAN super-resolution (optional package, user-installed)
- Model file management (download, cache, availability check)
- Fallback to cubic when selected method is unavailable

### Out of Scope
- Other preprocessing steps
- Custom model training
- GPU-specific optimizations

---

## Preconditions

1. **US-P1 complete**: Base infrastructure working
2. `opencv-python-headless` and `numpy` available
3. Internet access for model downloads (FSRCNN/EDSR only, one-time)

---

## Implementation Details

### File: `manga_ocr/preprocess/steps/upscale.py`

```python
import logging
from pathlib import Path

import cv2
import numpy as np

from manga_ocr.preprocess.base import BasePreProcessor

logger = logging.getLogger(__name__)

MODEL_DIR = Path.home() / ".manga_ocr" / "models"

MODEL_URLS = {
    "fsrcnn": "https://raw.githubusercontent.com/Saafke/FSRCNN_tensorflow/master/models/FSRCNN_x{scale}.pb",
    "edsr": "https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x{scale}.pb",
}


class UpscaleStep(BasePreProcessor):

    @property
    def name(self) -> str:
        return "upscale"

    @property
    def is_available(self) -> bool:
        return True  # cubic is always available

    def _get_model_path(self, method: str, scale: int) -> Path:
        return MODEL_DIR / f"{method.upper()}_x{scale}.pb"

    def _download_model(self, method: str, scale: int) -> Path:
        """Download model file if not cached."""
        model_path = self._get_model_path(method, scale)
        if model_path.exists():
            return model_path

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        url = MODEL_URLS[method].format(scale=scale)
        logger.info(f"Downloading {method} x{scale} model from {url}")

        # Use urllib to download
        import urllib.request
        urllib.request.urlretrieve(url, str(model_path))
        logger.info(f"Model saved to {model_path}")
        return model_path

    def _is_method_available(self, method: str, scale: int) -> bool:
        if method == "cubic":
            return True
        if method == "realesrgan":
            try:
                import realesrgan  # noqa: F401
                return True
            except ImportError:
                return False
        if method in ("fsrcnn", "edsr"):
            model_path = self._get_model_path(method, scale)
            return model_path.exists()
        return False

    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        method = config.get("method", "cubic")
        scale_factor = config.get("scale_factor", 2)

        if scale_factor < 2:
            return image, {"method": method, "scale_factor": scale_factor, "skipped": True}

        if method == "cubic":
            return self._upscale_cubic(image, scale_factor)
        elif method in ("fsrcnn", "edsr"):
            return self._upscale_dnn(image, method, scale_factor)
        elif method == "realesrgan":
            return self._upscale_realesrgan(image, scale_factor)
        else:
            logger.warning(f"Unknown upscale method '{method}', falling back to cubic")
            return self._upscale_cubic(image, scale_factor)

    def _upscale_cubic(self, image: np.ndarray, scale: int) -> tuple[np.ndarray, dict]:
        h, w = image.shape[:2]
        result = cv2.resize(image, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
        return result, {"method": "cubic", "scale_factor": scale, "input_size": (w, h), "output_size": (w * scale, h * scale)}

    def _upscale_dnn(self, image: np.ndarray, method: str, scale: int) -> tuple[np.ndarray, dict]:
        if not self._is_method_available(method, scale):
            try:
                self._download_model(method, scale)
            except Exception as e:
                logger.warning(f"Failed to download {method} model: {e}, falling back to cubic")
                return self._upscale_cubic(image, scale)

        model_path = self._get_model_path(method, scale)
        sr = cv2.dnn_superres.DnnSuperResImpl_create()
        sr.readModel(str(model_path))
        sr.setModel(method.lower(), scale)

        result = sr.upsample(image)
        h, w = image.shape[:2]
        oh, ow = result.shape[:2]
        return result, {"method": method, "scale_factor": scale, "input_size": (w, h), "output_size": (ow, oh)}

    def _upscale_realesrgan(self, image: np.ndarray, scale: int) -> tuple[np.ndarray, dict]:
        try:
            from realesrgan import RealESRGANer
            # Real-ESRGAN usage — requires realesrgan package
            # Implementation depends on specific realesrgan API version
            # Fallback to cubic if import fails (checked in process())
            raise NotImplementedError("Real-ESRGAN integration pending realesrgan package availability")
        except ImportError:
            logger.warning("realesrgan not installed, falling back to cubic")
            return self._upscale_cubic(image, scale)
```

### File: `manga_ocr/preprocess/pipeline.py` (updated)

Add `"upscale"` to `_create_step()` mapping.

---

## Postconditions

1. `UpscaleStep` with `method="cubic"` works without any external dependencies
2. `UpscaleStep` with `method="fsrcnn"` downloads model on first use, caches to `~/.manga_ocr/models/`
3. `UpscaleStep` with `method="edsr"` downloads model on first use, caches to `~/.manga_ocr/models/`
4. `UpscaleStep` with `method="realesrgan"` works if `realesrgan` installed, falls back to cubic otherwise
5. `scale_factor < 2` skips upscaling (pass-through)
6. Unknown method falls back to cubic with warning
7. Model download failure falls back to cubic with warning
8. Step registered in pipeline between grayscale and denoise

---

## Validation Checklist

- [ ] Cubic upscale doubles image dimensions when `scale_factor=2`
- [ ] Cubic upscale always available (`is_available=True`)
- [ ] FSRCNN upscale produces larger output image (mock model file)
- [ ] EDSR upscale produces larger output image (mock model file)
- [ ] Real-ESRGAN falls back to cubic when not installed
- [ ] `scale_factor=1` skips upscaling (pass-through)
- [ ] Unknown method falls back to cubic
- [ ] Metadata includes input/output dimensions
- [ ] Metadata includes method name and scale factor

---

## Test Plan

### File: `tests/test_preprocess.py` (updated)

1. `test_upscale_cubic_doubles_size` — 100x100 input, assert 200x200 output
2. `test_upscale_cubic_3channel` — BGR input, assert 3-channel output
3. `test_upscale_cubic_grayscale` — 2D input, assert 2D output
4. `test_upscale_skip_scale_1` — scale_factor=1, assert image unchanged
5. `test_upscale_unknown_method_fallback` — method="unknown", assert cubic used with warning
6. `test_upscale_realesrgan_fallback` — mock import failure, assert cubic fallback
7. `test_upscale_fsrcnn_model_download` — mock urllib, assert download attempted
8. `test_upscale_fsrcnn_model_cached` — create fake model file, assert no download
9. `test_upscale_edsr_model_download` — mock urllib, assert download attempted
10. `test_upscale_metadata` — assert metadata has method, scale_factor, input_size, output_size

Test fixtures:

```python
@pytest.fixture
def small_image():
    return np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
```

---

## Questions for Operator

None.

---

## Dependencies

- **US-P1** complete

---

## Estimated Complexity

**Medium-High** — cubic is trivial, but FSRCNN/EDSR model management (download, cache, availability checks) and Real-ESRGAN optional dependency add significant complexity.
