"""Preprocessing pipeline that chains image transformation steps."""

import logging
import os
import time
from pathlib import Path

import cv2
import numpy as np

from ocr_manga_title.preprocess.base import BasePreProcessor
from ocr_manga_title.schemas import PreProcessResult, PreProcessStepResult

logger = logging.getLogger(__name__)


class PreProcessingPipeline:
    """Ordered pipeline of image preprocessing steps.

    Steps are executed in the order defined by :attr:`STEP_ORDER`. Each step
    can be individually enabled or disabled via the configuration dict.
    """

    STEP_ORDER = ["roi", "grayscale", "upscale", "denoise", "binarize"]

    def __init__(self, config: dict):
        self._config = config.get("preprocessing", {})
        self._debug = self._config.get("debug", False)
        self._steps: list[BasePreProcessor] = self._initialize_steps()

    def _initialize_steps(self) -> list[BasePreProcessor]:
        steps = []
        for step_name in self.STEP_ORDER:
            step = self._create_step(step_name)
            if step is not None:
                steps.append(step)
        return steps

    def _create_step(self, name: str) -> BasePreProcessor | None:
        from ocr_manga_title.preprocess.steps.binarize import BinarizeStep
        from ocr_manga_title.preprocess.steps.denoise import DenoiseStep
        from ocr_manga_title.preprocess.steps.grayscale import GrayscaleStep
        from ocr_manga_title.preprocess.steps.roi import ROIStep
        from ocr_manga_title.preprocess.steps.upscale import UpscaleStep

        steps_map: dict[str, type[BasePreProcessor]] = {
            "roi": ROIStep,
            "grayscale": GrayscaleStep,
            "binarize": BinarizeStep,
            "upscale": UpscaleStep,
            "denoise": DenoiseStep,
        }

        step_cls = steps_map.get(name)
        if step_cls is not None:
            step = step_cls()
            if step.is_available:
                return step
            logger.warning("Preprocessing step '%s' not available", name)
        return None

    def _save_image(self, image: np.ndarray, label: str, uid: str) -> str:
        import tempfile

        out_dir = Path(tempfile.gettempdir()) / "manga_ocr_preprocess"
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uid}_{label}.png"
        path = out_dir / filename
        cv2.imwrite(str(path), image)
        return str(path)

    def process(self, image_path: str) -> PreProcessResult:
        """Run all enabled steps on the image sequentially.

        Args:
            image_path: Path to the source image.

        Returns:
            :class:`~ocr_manga_title.schemas.PreProcessResult` with per-step
            details and the path to the final processed image.

        """
        start_time = time.monotonic()
        uid = f"{time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}_{id(image_path)}"
        step_results: list[PreProcessStepResult] = []

        image = cv2.imread(image_path)
        if image is None:
            return PreProcessResult(
                input_path=image_path,
                output_path=None,
                steps=[
                    PreProcessStepResult(
                        step_name="load",
                        enabled=True,
                        success=False,
                        processing_time_ms=0,
                        error=f"Failed to read image: {image_path}",
                    )
                ],
                total_processing_time_ms=0,
            )

        current_image: np.ndarray = image
        final_output_path: str | None = None

        for step in self._steps:
            step_config = self._config.get(step.name, {})
            enabled = step_config.get("enabled", True)

            if not enabled:
                step_results.append(
                    PreProcessStepResult(
                        step_name=step.name,
                        enabled=False,
                        success=True,
                        processing_time_ms=0,
                    )
                )
                continue

            step_start = time.monotonic()
            try:
                result_image, metadata = step.process(current_image, step_config)
                step_time_ms = int((time.monotonic() - step_start) * 1000)

                output_path = None
                if self._debug and result_image is not None:
                    output_path = self._save_image(result_image, step.name, uid)

                step_results.append(
                    PreProcessStepResult(
                        step_name=step.name,
                        enabled=True,
                        success=True,
                        processing_time_ms=step_time_ms,
                        output_path=output_path,
                        metadata=metadata,
                    )
                )
                current_image = result_image
                final_output_path = output_path
            except Exception as e:
                step_time_ms = int((time.monotonic() - step_start) * 1000)
                logger.error("Preprocessing step '%s' failed: %s", step.name, e)
                step_results.append(
                    PreProcessStepResult(
                        step_name=step.name,
                        enabled=True,
                        success=False,
                        processing_time_ms=step_time_ms,
                        error=str(e),
                    )
                )

        total_time_ms = int((time.monotonic() - start_time) * 1000)

        if any(s.success and s.enabled for s in step_results):
            final_output_path = self._save_image(current_image, "output", uid)

        return PreProcessResult(
            input_path=image_path,
            output_path=final_output_path,
            steps=step_results,
            total_processing_time_ms=total_time_ms,
        )
