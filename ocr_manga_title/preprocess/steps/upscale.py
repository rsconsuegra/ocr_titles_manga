"""Image upscaling step supporting cubic interpolation and DNN-based super-resolution."""

import hashlib
import logging
from pathlib import Path

import cv2
import numpy as np

from ocr_manga_title.preprocess.base import BasePreProcessor

logger = logging.getLogger(__name__)

MODEL_DIR = Path.home() / ".ocr_manga_title" / "models"

MODEL_URLS = {
    "fsrcnn": "https://raw.githubusercontent.com/Saafke/FSRCNN_tensorflow/master/models/FSRCNN_x{scale}.pb",
    "edsr": "https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x{scale}.pb",
}

_MODEL_HASHES: dict[str, str] = {
    "FSRCNN_x2.pb": "sha256:placeholder_replace_with_actual_hash",
    "FSRCNN_x3.pb": "sha256:placeholder_replace_with_actual_hash",
    "FSRCNN_x4.pb": "sha256:placeholder_replace_with_actual_hash",
    "EDSR_x2.pb": "sha256:placeholder_replace_with_actual_hash",
    "EDSR_x3.pb": "sha256:placeholder_replace_with_actual_hash",
    "EDSR_x4.pb": "sha256:placeholder_replace_with_actual_hash",
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

        import urllib.request

        urllib.request.urlretrieve(url, str(model_path))

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

    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        """Upscale the image using the configured method and scale factor."""
        method = config.get("method", "cubic")
        scale_factor = config.get("scale_factor", 2)

        if scale_factor < 2:
            return image, {
                "method": method,
                "scale_factor": scale_factor,
                "skipped": True,
            }

        if method == "cubic":
            return self._upscale_cubic(image, scale_factor)
        elif method in ("fsrcnn", "edsr"):
            return self._upscale_dnn(image, method, scale_factor)
        elif method == "realesrgan":
            return self._upscale_realesrgan(image, scale_factor)
        else:
            logger.warning("Unknown upscale method '%s', falling back to cubic", method)
            return self._upscale_cubic(image, scale_factor)

    def _upscale_cubic(self, image: np.ndarray, scale: int) -> tuple[np.ndarray, dict]:
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

    def _upscale_dnn(
        self, image: np.ndarray, method: str, scale: int
    ) -> tuple[np.ndarray, dict]:
        if not self._is_method_available(method, scale):
            try:
                self._download_model(method, scale)
            except Exception as e:
                logger.warning(
                    "Failed to download %s model: %s, falling back to cubic", method, e
                )
                return self._upscale_cubic(image, scale)

        model_path = self._get_model_path(method, scale)
        sr = cv2.dnn_superres.DnnSuperResImpl_create()
        sr.readModel(str(model_path))
        sr.setModel(method.lower(), scale)

        result = sr.upsample(image)
        h, w = image.shape[:2]
        oh, ow = result.shape[:2]
        return result, {
            "method": method,
            "scale_factor": scale,
            "input_size": (w, h),
            "output_size": (ow, oh),
        }

    def _upscale_realesrgan(
        self, image: np.ndarray, scale: int
    ) -> tuple[np.ndarray, dict]:
        try:
            import realesrgan  # noqa: F401

            raise NotImplementedError(
                "Real-ESRGAN integration pending realesrgan package setup"
            )
        except ImportError:
            logger.warning("realesrgan not installed, falling back to cubic")
            return self._upscale_cubic(image, scale)
