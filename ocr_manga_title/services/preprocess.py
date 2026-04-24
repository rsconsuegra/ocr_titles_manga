"""Preprocessing execution service — shared by routes and worker."""

from ocr_manga_title.preprocess.registry import STEP_ORDER
from ocr_manga_title.services.image import decode_image, numpy_to_temp_file


def get_step_instance(step_name: str):
    """Instantiate a preprocessing step by name."""
    from ocr_manga_title.preprocess.steps.binarize import BinarizeStep
    from ocr_manga_title.preprocess.steps.denoise import DenoiseStep
    from ocr_manga_title.preprocess.steps.grayscale import GrayscaleStep
    from ocr_manga_title.preprocess.steps.roi import ROIStep
    from ocr_manga_title.preprocess.steps.upscale import UpscaleStep

    steps_map = {
        "roi": ROIStep,
        "grayscale": GrayscaleStep,
        "upscale": UpscaleStep,
        "denoise": DenoiseStep,
        "binarize": BinarizeStep,
    }
    cls = steps_map.get(step_name)
    if cls is None:
        raise ValueError(f"Unknown step: {step_name}")
    return cls()


def run_preprocessing_pipeline(
    image_data_url: str,
    steps_config: dict,
) -> str:
    """Run preprocessing on a data URL. Returns path to processed image."""
    current_image = decode_image(image_data_url)
    has_steps = False

    for step_name in STEP_ORDER:
        step_config = dict(steps_config.get(step_name, {}))
        enabled = step_config.pop("enabled", False)
        if not enabled:
            continue
        has_steps = True
        step = get_step_instance(step_name)
        current_image, _ = step.process(current_image, step_config)

    return numpy_to_temp_file(current_image)
