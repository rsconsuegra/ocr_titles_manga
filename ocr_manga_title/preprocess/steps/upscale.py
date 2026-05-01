"""Image upscaling step supporting cubic interpolation and DNN-based super-resolution."""

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from ocr_manga_title.preprocess.base import BasePreProcessor

logger = logging.getLogger(__name__)

MODEL_DIR = Path(os.getenv("MODEL_DIR", Path.home() / ".ocr_manga_title" / "models"))

DNN_MEMORY_OVERHEAD = {
    "fsrcnn": 3,
    "edsr": 8,
}

MEMORY_SAFETY_FACTOR = 0.6

MODEL_URLS = {
    "fsrcnn": "https://raw.githubusercontent.com/Saafke/FSRCNN_tensorflow/master/models/FSRCNN_x{scale}.pb",
    "edsr": "https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x{scale}.pb",
}

_MODEL_HASHES: dict[str, str] = {
    "FSRCNN_x2.pb": "sha256:366b33f0084c7b3f2bf6724f0a2c77bca94fcec9d7b6d72389d330073b380d5c",
    "FSRCNN_x3.pb": "sha256:efd38655a815908c6c8954db6052f128e76a735f1de657894c477d0dc0b64481",
    "FSRCNN_x4.pb": "sha256:5c68d18db561aed8ead4ffedf1b897ea615baaf60ebf6c35f8e641f8fa4a21bf",
    "EDSR_x2.pb": "sha256:585623221baa070279a0d1e7e113a4c3faba0f318ca7fdd9a65d9afc0763d9b4",
    "EDSR_x3.pb": "sha256:3baa3740fdb8ee9c52f1a41d69fa74cb9feef0fa9bfeec24f0ee58b928068e9a",
    "EDSR_x4.pb": "sha256:dd35ce3cae53ecee2d16045e08a932c3e7242d641bb65cb971d123e06904347f",
}


class UpscaleStep(BasePreProcessor):
    """Upscales images using cubic interpolation or DNN super-resolution models."""

    @property
    def name(self) -> str:
        """Machine-readable identifier for this step."""
        return "upscale"

    @property
    def is_available(self) -> bool:
        """Whether the step's runtime dependencies are installed."""
        return True

    @property
    def timeout(self) -> int:
        """DNN upscaling can be slow on large images."""
        return 300

    def _get_model_path(self, method: str, scale: int) -> Path:
        return MODEL_DIR / f"{method.upper()}_x{scale}.pb"

    def _verify_model_hash(self, model_path: Path) -> bool:
        expected = _MODEL_HASHES.get(model_path.name)
        if expected is None:
            logger.warning(
                "No known hash for model %s — skipping integrity check",
                model_path.name,
            )
            return True
        algo, _, expected_hex = expected.partition(":")
        actual_hex = hashlib.new(algo, model_path.read_bytes()).hexdigest()
        if actual_hex != expected_hex:
            logger.error(
                "Hash mismatch for %s (expected %s, got %s)",
                model_path.name,
                expected_hex[:12],
                actual_hex[:12],
            )
            return False
        return True

    def _download_model(self, method: str, scale: int) -> Path:
        model_path = self._get_model_path(method, scale)
        if model_path.exists():
            if self._verify_model_hash(model_path):
                return model_path
            logger.warning(
                "Existing model %s failed hash check — re-downloading", model_path.name
            )
            model_path.unlink(missing_ok=True)

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        url = MODEL_URLS[method].format(scale=scale)
        logger.info("Downloading %s x%d model from %s", method, scale, url)

        import urllib.error
        import urllib.request

        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                model_path.write_bytes(resp.read())
        except (OSError, urllib.error.URLError) as e:
            model_path.unlink(missing_ok=True)
            raise RuntimeError(f"Failed to download {model_path.name}: {e}") from e

        if not self._verify_model_hash(model_path):
            model_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Downloaded model {model_path.name} failed integrity verification"
            )

        logger.info("Model saved to %s", model_path)
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
            return self._get_model_path(method, scale).exists()
        return False

    def process(self, image: np.ndarray, config: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        """Upscale the image according to the provided config."""
        method = config.get("method", "cubic")
        scale_factor = config.get("scale_factor", 2)

        start = time.monotonic()
        logger.info("Upscaling with %s x%d started", method.upper(), scale_factor)

        if scale_factor < 2:
            logger.info("Upscaling skipped (scale_factor < 2)")
            return image, {
                "method": method,
                "scale_factor": scale_factor,
                "skipped": True,
            }

        if method == "cubic":
            result, meta = self._upscale_cubic(image, scale_factor)
        elif method in ("fsrcnn", "edsr"):
            result, meta = self._upscale_dnn(image, method, scale_factor)
        elif method == "realesrgan":
            result, meta = self._upscale_realesrgan(image, scale_factor)
        else:
            logger.warning("Unknown upscale method '%s', falling back to cubic", method)
            result, meta = self._upscale_cubic(image, scale_factor)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info("Upscaling with %s x%d finished in %dms", method.upper(), scale_factor, elapsed_ms)
        return result, meta

    def _upscale_cubic(self, image: np.ndarray, scale: int) -> tuple[np.ndarray, dict[str, Any]]:
        h, w = image.shape[:2]
        result = cv2.resize(
            image, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC
        )
        meta = {
            "method": "cubic",
            "scale_factor": scale,
            "input_size": (w, h),
            "output_size": (w * scale, h * scale),
        }
        return result, meta

    @staticmethod
    def _available_memory_bytes() -> int:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) * 1024
        except (OSError, ValueError):
            logger.debug("/proc/meminfo unavailable — upscale memory guard disabled")
        return 0

    def _estimate_dnn_peak_bytes(self, h: int, w: int, method: str, scale: int) -> int:
        overhead = DNN_MEMORY_OVERHEAD.get(method, 6)
        output_pixels = h * w * scale * scale
        return output_pixels * 3 * 4 * overhead

    def _upscale_dnn(
        self, image: np.ndarray, method: str, scale: int
    ) -> tuple[np.ndarray, dict[str, Any]]:
        h, w = image.shape[:2]
        estimated_peak = self._estimate_dnn_peak_bytes(h, w, method, scale)
        available = self._available_memory_bytes()

        if available > 0:
            budget = available * MEMORY_SAFETY_FACTOR
            if estimated_peak > budget:
                raise ValueError(
                    f"Insufficient memory for {method.upper()} x{scale} upscaling "
                    f"({w}x{h} → {w * scale}x{h * scale}). "
                    f"Estimated peak: {estimated_peak / 1e9:.1f} GB, "
                    f"available budget: {budget / 1e9:.1f} GB "
                    f"({available / 1e9:.1f} GB RAM available × "
                    f"{MEMORY_SAFETY_FACTOR:.0%} safety margin). "
                    f"Use a smaller image, lower scale factor, or cubic interpolation."
                )
            logger.info(
                "DNN memory check: estimated %.1f GB peak vs %.1f GB budget",
                estimated_peak / 1e9,
                budget / 1e9,
            )

        if not self._is_method_available(method, scale):
            try:
                self._download_model(method, scale)
            except RuntimeError as e:
                raise RuntimeError(
                    f"Failed to download {method.upper()} model: {e}"
                ) from e

        model_path = self._get_model_path(method, scale)
        sr = cv2.dnn_superres.DnnSuperResImpl_create()  # type: ignore[attr-defined]
        sr.readModel(str(model_path))
        sr.setModel(method.lower(), scale)

        grayscale_input = image.ndim == 2
        if grayscale_input:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        try:
            result = sr.upsample(image)
        except (MemoryError, cv2.error) as e:
            raise RuntimeError(
                f"{method.upper()} x{scale} upscaling ran out of memory on "
                f"{w}x{h} image ({available / 1e9:.1f} GB RAM available). "
                f"Use a smaller image, lower scale factor, or cubic interpolation."
            ) from e

        if grayscale_input:
            result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

        oh, ow = result.shape[:2]
        return result, {
            "method": method,
            "scale_factor": scale,
            "input_size": (w, h),
            "output_size": (ow, oh),
            "grayscale_input": grayscale_input,
        }

    def _upscale_realesrgan(
        self, image: np.ndarray, scale: int
    ) -> tuple[np.ndarray, dict[str, Any]]:
        try:
            import realesrgan  # noqa: F401
        except ImportError:
            logger.warning("realesrgan not installed, falling back to cubic")
            return self._upscale_cubic(image, scale)
        raise NotImplementedError(
            "Real-ESRGAN integration pending realesrgan package setup"
        )
