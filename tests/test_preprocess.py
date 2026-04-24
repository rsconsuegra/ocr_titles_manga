"""Tests for image preprocessing pipeline (US-P1 through US-P7)."""

import numpy as np
import pytest

from ocr_manga_title.config import load_preprocess_config
from ocr_manga_title.preprocess.base import BasePreProcessor
from ocr_manga_title.preprocess.steps.binarize import BinarizeStep
from ocr_manga_title.preprocess.steps.denoise import DenoiseStep
from ocr_manga_title.preprocess.steps.grayscale import GrayscaleStep
from ocr_manga_title.preprocess.steps.roi import ROIStep
from ocr_manga_title.preprocess.steps.upscale import UpscaleStep
from ocr_manga_title.schemas import (
    PipelineResult,
    PreProcessResult,
    PreProcessStepResult,
)


@pytest.fixture
def bgr_image():
    return np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)


@pytest.fixture
def bgra_image():
    return np.random.randint(0, 255, (100, 100, 4), dtype=np.uint8)


@pytest.fixture
def gray_image():
    return np.random.randint(0, 255, (100, 100), dtype=np.uint8)


@pytest.fixture
def small_image():
    return np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)


@pytest.fixture
def valid_preprocess_yaml(tmp_path):
    yaml_content = """
preprocessing:
  enabled: true
  debug: false
  grayscale:
    enabled: true
  upscale:
    enabled: true
    method: "cubic"
    scale_factor: 2
  denoise:
    enabled: true
    method: "gaussian"
    strength: "light"
  binarize:
    enabled: true
    method: "otsu"
"""
    yaml_file = tmp_path / "preprocess.yaml"
    yaml_file.write_text(yaml_content)
    return yaml_file


@pytest.fixture
def test_image_file(tmp_path, bgr_image):
    import cv2

    path = tmp_path / "test_image.png"
    cv2.imwrite(str(path), bgr_image)
    return str(path)


class TestPreProcessConfig:
    def test_load_preprocess_config_valid(self, valid_preprocess_yaml):
        config = load_preprocess_config(valid_preprocess_yaml)
        assert config["preprocessing"]["enabled"] is True

    def test_load_preprocess_config_missing_file(self, tmp_path):
        config = load_preprocess_config(tmp_path / "nonexistent.yaml")
        assert config["preprocessing"]["enabled"] is False

    def test_load_preprocess_config_empty_file(self, tmp_path):
        yaml_file = tmp_path / "preprocess.yaml"
        yaml_file.write_text("")
        config = load_preprocess_config(yaml_file)
        assert config["preprocessing"]["enabled"] is False

    def test_load_preprocess_config_missing_preprocessing_key(self, tmp_path):
        yaml_file = tmp_path / "preprocess.yaml"
        yaml_file.write_text("other_key: value\n")
        config = load_preprocess_config(yaml_file)
        assert config["preprocessing"]["enabled"] is False


class TestPreProcessSchemas:
    def test_preprocess_step_result_valid(self):
        step = PreProcessStepResult(
            step_name="grayscale", enabled=True, success=True, processing_time_ms=5
        )
        assert step.step_name == "grayscale"
        assert step.metadata == {}

    def test_preprocess_result_with_steps(self):
        step = PreProcessStepResult(
            step_name="grayscale", enabled=True, success=True, processing_time_ms=5
        )
        result = PreProcessResult(
            input_path="/test.png", steps=[step], total_processing_time_ms=10
        )
        assert len(result.steps) == 1
        assert result.output_path is None

    def test_pipeline_result_with_preprocess_result(self):
        step = PreProcessStepResult(
            step_name="grayscale", enabled=True, success=True, processing_time_ms=5
        )
        pp = PreProcessResult(input_path="/test.png", steps=[step])
        result = PipelineResult(input_path="/test.png", preprocess_result=pp)
        assert result.preprocess_result is not None
        assert len(result.preprocess_result.steps) == 1

    def test_pipeline_result_without_preprocess_result(self):
        result = PipelineResult(input_path="/test.png")
        assert result.preprocess_result is None


class TestBasePreProcessor:
    def test_base_preprocessor_is_abstract(self):
        with pytest.raises(TypeError):
            BasePreProcessor()


class TestGrayscaleStep:
    def test_grayscale_3channel(self, bgr_image):
        step = GrayscaleStep()
        result, meta = step.process(bgr_image, {})
        assert result.ndim == 2
        assert result.shape == (100, 100)

    def test_grayscale_4channel(self, bgra_image):
        step = GrayscaleStep()
        result, meta = step.process(bgra_image, {})
        assert result.ndim == 2

    def test_grayscale_already_gray(self, gray_image):
        step = GrayscaleStep()
        result, meta = step.process(gray_image, {})
        assert result is gray_image

    def test_grayscale_metadata_converted(self, bgr_image):
        step = GrayscaleStep()
        _, meta = step.process(bgr_image, {})
        assert meta["original_channels"] == 3
        assert meta["converted"] is True

    def test_grayscale_metadata_passthrough(self, gray_image):
        step = GrayscaleStep()
        _, meta = step.process(gray_image, {})
        assert meta["original_channels"] == 1
        assert meta["converted"] is False

    def test_grayscale_always_available(self):
        assert GrayscaleStep().is_available is True

    def test_grayscale_name(self):
        assert GrayscaleStep().name == "grayscale"


class TestBinarizeStep:
    def test_binarize_otsu(self, gray_image):
        step = BinarizeStep()
        result, meta = step.process(gray_image, {"method": "otsu"})
        assert result.ndim == 2
        assert set(np.unique(result)).issubset({0, 255})
        assert meta["method"] == "otsu"
        assert "threshold" in meta

    def test_binarize_adaptive_gaussian(self, gray_image):
        step = BinarizeStep()
        result, meta = step.process(gray_image, {"method": "adaptive_gaussian"})
        assert result.ndim == 2
        assert meta["method"] == "adaptive_gaussian"

    def test_binarize_adaptive_mean(self, gray_image):
        step = BinarizeStep()
        result, meta = step.process(gray_image, {"method": "adaptive_mean"})
        assert result.ndim == 2
        assert meta["method"] == "adaptive_mean"

    def test_binarize_invert(self, gray_image):
        step = BinarizeStep()
        normal, _ = step.process(gray_image, {"method": "otsu", "invert": False})
        inverted, _ = step.process(gray_image, {"method": "otsu", "invert": True})
        assert np.array_equal(normal, 255 - inverted)

    def test_binarize_color_input_auto_converts(self, bgr_image):
        step = BinarizeStep()
        result, _ = step.process(bgr_image, {"method": "otsu"})
        assert result.ndim == 2

    def test_binarize_invalid_method_raises(self, gray_image):
        step = BinarizeStep()
        with pytest.raises(ValueError, match="Unknown binarization method"):
            step.process(gray_image, {"method": "unknown"})

    def test_binarize_even_block_size_corrected(self, gray_image):
        step = BinarizeStep()
        result, meta = step.process(
            gray_image, {"method": "adaptive_gaussian", "block_size": 10}
        )
        assert meta["block_size"] == 11
        assert result.ndim == 2

    def test_binarize_small_block_size_corrected(self, gray_image):
        step = BinarizeStep()
        result, meta = step.process(
            gray_image, {"method": "adaptive_mean", "block_size": 1}
        )
        assert meta["block_size"] == 3
        assert result.ndim == 2

    def test_binarize_always_available(self):
        assert BinarizeStep().is_available is True

    def test_binarize_name(self):
        assert BinarizeStep().name == "binarize"


class TestUpscaleStep:
    def test_upscale_cubic_doubles_size(self, small_image):
        step = UpscaleStep()
        result, meta = step.process(small_image, {"method": "cubic", "scale_factor": 2})
        assert result.shape[:2] == (100, 100)
        assert meta["output_size"] == (100, 100)

    def test_upscale_cubic_3channel(self, bgr_image):
        step = UpscaleStep()
        result, meta = step.process(bgr_image, {"method": "cubic", "scale_factor": 2})
        assert result.ndim == 3
        assert result.shape[2] == 3

    def test_upscale_cubic_grayscale(self, gray_image):
        step = UpscaleStep()
        result, meta = step.process(gray_image, {"method": "cubic", "scale_factor": 2})
        assert result.ndim == 2
        assert result.shape == (200, 200)

    def test_upscale_skip_scale_1(self, gray_image):
        step = UpscaleStep()
        result, meta = step.process(gray_image, {"method": "cubic", "scale_factor": 1})
        assert result is gray_image
        assert meta["skipped"] is True

    def test_upscale_unknown_method_fallback(self, gray_image):
        step = UpscaleStep()
        result, meta = step.process(
            gray_image, {"method": "unknown", "scale_factor": 2}
        )
        assert meta["method"] == "cubic"

    def test_upscale_realesrgan_fallback(self, gray_image):
        step = UpscaleStep()
        result, meta = step.process(
            gray_image, {"method": "realesrgan", "scale_factor": 2}
        )
        assert meta["method"] == "cubic"

    def test_upscale_metadata(self, gray_image):
        step = UpscaleStep()
        _, meta = step.process(gray_image, {"method": "cubic", "scale_factor": 2})
        assert meta["method"] == "cubic"
        assert meta["scale_factor"] == 2
        assert meta["input_size"] == (100, 100)
        assert meta["output_size"] == (200, 200)

    def test_upscale_always_available(self):
        assert UpscaleStep().is_available is True

    def test_upscale_name(self):
        assert UpscaleStep().name == "upscale"

    def test_upscale_fsrcnn_model_cached(self, gray_image, tmp_path, monkeypatch):
        from ocr_manga_title.preprocess.steps.upscale import UpscaleStep

        monkeypatch.setattr(
            "ocr_manga_title.preprocess.steps.upscale.MODEL_DIR", tmp_path
        )
        model_path = tmp_path / "FSRCNN_x2.pb"
        model_path.write_bytes(b"fake_model")

        step = UpscaleStep()
        assert step._is_method_available("fsrcnn", 2) is True

    def test_upscale_edsr_model_cached(self, gray_image, tmp_path, monkeypatch):
        from ocr_manga_title.preprocess.steps.upscale import UpscaleStep

        monkeypatch.setattr(
            "ocr_manga_title.preprocess.steps.upscale.MODEL_DIR", tmp_path
        )
        model_path = tmp_path / "EDSR_x2.pb"
        model_path.write_bytes(b"fake_model")

        step = UpscaleStep()
        assert step._is_method_available("edsr", 2) is True


class TestDenoiseStep:
    def test_denoise_gaussian_light(self, gray_image):
        step = DenoiseStep()
        result, meta = step.process(
            gray_image, {"method": "gaussian", "strength": "light"}
        )
        assert result.shape == gray_image.shape
        assert meta["params"]["ksize"] == 3

    def test_denoise_gaussian_medium(self, gray_image):
        step = DenoiseStep()
        result, meta = step.process(
            gray_image, {"method": "gaussian", "strength": "medium"}
        )
        assert meta["params"]["ksize"] == 5

    def test_denoise_gaussian_heavy(self, gray_image):
        step = DenoiseStep()
        result, meta = step.process(
            gray_image, {"method": "gaussian", "strength": "heavy"}
        )
        assert meta["params"]["ksize"] == 7

    def test_denoise_median_light(self, gray_image):
        step = DenoiseStep()
        result, meta = step.process(
            gray_image, {"method": "median", "strength": "light"}
        )
        assert meta["params"]["ksize"] == 3

    def test_denoise_nlmeans_grayscale(self, gray_image):
        step = DenoiseStep()
        result, meta = step.process(
            gray_image, {"method": "nlmeans", "strength": "light"}
        )
        assert result.shape == gray_image.shape
        assert meta["params"]["h"] == 3

    def test_denoise_nlmeans_color(self, bgr_image):
        step = DenoiseStep()
        result, meta = step.process(
            bgr_image, {"method": "nlmeans", "strength": "medium"}
        )
        assert result.shape == bgr_image.shape
        assert meta["params"]["h"] == 6

    def test_denoise_invalid_method_fallback(self, gray_image):
        step = DenoiseStep()
        result, meta = step.process(gray_image, {"method": "unknown"})
        assert meta["method"] == "gaussian"

    def test_denoise_invalid_strength_fallback(self, gray_image):
        step = DenoiseStep()
        result, meta = step.process(
            gray_image, {"method": "gaussian", "strength": "extreme"}
        )
        assert meta["strength"] == "light"

    def test_denoise_preserves_dimensions(self, bgr_image):
        step = DenoiseStep()
        result, _ = step.process(bgr_image, {"method": "gaussian"})
        assert result.shape == bgr_image.shape

    def test_denoise_metadata(self, gray_image):
        step = DenoiseStep()
        _, meta = step.process(gray_image, {"method": "gaussian", "strength": "light"})
        assert meta["method"] == "gaussian"
        assert meta["strength"] == "light"
        assert "params" in meta

    def test_denoise_always_available(self):
        assert DenoiseStep().is_available is True

    def test_denoise_name(self):
        assert DenoiseStep().name == "denoise"


@pytest.fixture
def text_like_image():
    img = np.zeros((200, 200), dtype=np.uint8)
    img[50:150, 30:170] = 255
    return img


@pytest.fixture
def text_like_color_image():
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    img[50:150, 30:170] = (255, 255, 255)
    return img


@pytest.fixture
def blank_image():
    return np.zeros((200, 200), dtype=np.uint8)


@pytest.fixture
def full_coverage_image():
    img = np.zeros((200, 200), dtype=np.uint8)
    img[5:195, 5:195] = 255
    return img


class TestROIStep:
    def test_roi_contour_detects_text(self, text_like_image):
        step = ROIStep()
        result, meta = step.process(text_like_image, {"method": "contour"})
        assert meta["crop_performed"] is True
        assert meta["regions_detected"] >= 1
        assert (
            result.shape[0] < text_like_image.shape[0]
            or result.shape[1] < text_like_image.shape[1]
        )

    def test_roi_no_regions(self, blank_image):
        step = ROIStep()
        result, meta = step.process(blank_image, {"method": "contour"})
        assert meta["regions_detected"] == 0
        assert meta["crop_performed"] is False
        assert result is blank_image

    def test_roi_small_image_skip(self):
        step = ROIStep()
        small = np.random.randint(0, 255, (50, 50), dtype=np.uint8)
        result, meta = step.process(small, {"method": "contour"})
        assert meta["crop_performed"] is False
        assert meta["reason"] == "image_too_small"
        assert result is small

    def test_roi_large_coverage_skip(self, full_coverage_image):
        step = ROIStep()
        result, meta = step.process(full_coverage_image, {"method": "contour"})
        assert meta["crop_performed"] is False
        assert meta["reason"] == "coverage_too_large"

    def test_roi_padding_applied(self, text_like_image):
        step = ROIStep()
        result, meta = step.process(
            text_like_image, {"method": "contour", "padding": 20}
        )
        if meta["crop_performed"]:
            bb = meta["bounding_box"]
            assert bb["w"] >= 140 - 40 + 40
            assert bb["h"] >= 100 - 40 + 40

    def test_roi_padding_clamped(self):
        step = ROIStep()
        img = np.zeros((200, 200), dtype=np.uint8)
        img[0:30, 0:30] = 255
        result, meta = step.process(img, {"method": "contour", "padding": 50})
        if meta["crop_performed"]:
            bb = meta["bounding_box"]
            assert bb["x"] == 0
            assert bb["y"] == 0

    def test_roi_merge_overlapping(self):
        step = ROIStep()
        img = np.zeros((200, 200), dtype=np.uint8)
        img[20:60, 20:60] = 255
        img[70:110, 70:110] = 255
        result, meta = step.process(img, {"method": "contour", "merge_overlap": 0.0})
        assert meta["regions_detected"] >= 2

    def test_roi_grayscale_input(self, text_like_image):
        step = ROIStep()
        result, meta = step.process(text_like_image, {"method": "contour"})
        assert "method" in meta
        assert meta["method"] == "contour"

    def test_roi_color_input(self, text_like_color_image):
        step = ROIStep()
        result, meta = step.process(text_like_color_image, {"method": "contour"})
        assert result.ndim == 3 or meta.get("crop_performed") is not None

    def test_roi_metadata_structure(self, text_like_image):
        step = ROIStep()
        _, meta = step.process(text_like_image, {"method": "contour"})
        assert "method" in meta
        assert "regions_detected" in meta
        assert "crop_performed" in meta

    def test_roi_always_available(self):
        assert ROIStep().is_available is True

    def test_roi_name(self):
        assert ROIStep().name == "roi"

    def test_roi_unknown_method(self, text_like_image):
        step = ROIStep()
        result, meta = step.process(text_like_image, {"method": "east"})
        assert meta["crop_performed"] is False
        assert meta["reason"] == "unknown_method"


class TestPreProcessingPipeline:
    def test_pipeline_init_with_steps(self, valid_preprocess_yaml, tmp_path):
        from ocr_manga_title.preprocess.pipeline import PreProcessingPipeline

        config = load_preprocess_config(valid_preprocess_yaml)
        pipeline = PreProcessingPipeline(config, tmp_path)
        step_names = [s.name for s in pipeline._steps]
        assert "grayscale" in step_names
        assert "binarize" in step_names
        assert "upscale" in step_names
        assert "denoise" in step_names

    def test_pipeline_init_with_all_steps(self, tmp_path):
        from ocr_manga_title.preprocess.pipeline import PreProcessingPipeline

        config = {
            "preprocessing": {
                "enabled": True,
                "debug": False,
                "roi": {"enabled": True, "method": "contour"},
                "grayscale": {"enabled": True},
                "upscale": {"enabled": True, "method": "cubic", "scale_factor": 2},
                "denoise": {"enabled": True, "method": "gaussian", "strength": "light"},
                "binarize": {"enabled": True, "method": "otsu"},
            }
        }
        pipeline = PreProcessingPipeline(config, tmp_path)
        step_names = [s.name for s in pipeline._steps]
        assert step_names == ["roi", "grayscale", "upscale", "denoise", "binarize"]

    def test_pipeline_process_all_steps(self, test_image_file, tmp_path):
        from ocr_manga_title.preprocess.pipeline import PreProcessingPipeline

        config = {
            "preprocessing": {
                "enabled": True,
                "debug": True,
                "roi": {"enabled": True, "method": "contour", "min_area": 100},
                "grayscale": {"enabled": True},
                "upscale": {"enabled": True, "method": "cubic", "scale_factor": 2},
                "denoise": {"enabled": True, "method": "gaussian", "strength": "light"},
                "binarize": {"enabled": True, "method": "otsu"},
            }
        }
        pipeline = PreProcessingPipeline(config, tmp_path)
        result = pipeline.process(test_image_file)
        assert isinstance(result, PreProcessResult)
        assert len(result.steps) == 5
        step_names = [s.step_name for s in result.steps]
        assert step_names == ["roi", "grayscale", "upscale", "denoise", "binarize"]

    def test_pipeline_process_returns_result(self, test_image_file, tmp_path):
        from ocr_manga_title.preprocess.pipeline import PreProcessingPipeline

        config = {
            "preprocessing": {
                "enabled": True,
                "debug": False,
                "grayscale": {"enabled": True},
                "upscale": {"enabled": True, "method": "cubic", "scale_factor": 2},
                "denoise": {"enabled": True, "method": "gaussian", "strength": "light"},
                "binarize": {"enabled": True, "method": "otsu"},
            }
        }
        pipeline = PreProcessingPipeline(config, tmp_path)
        result = pipeline.process(test_image_file)
        assert isinstance(result, PreProcessResult)
        assert result.input_path == test_image_file
        assert len(result.steps) == 5
        assert all(s.success for s in result.steps)
        assert result.total_processing_time_ms >= 0

    def test_pipeline_process_invalid_image(self, tmp_path):
        from ocr_manga_title.preprocess.pipeline import PreProcessingPipeline

        config = {"preprocessing": {"enabled": True, "debug": False}}
        pipeline = PreProcessingPipeline(config, tmp_path)
        result = pipeline.process("/nonexistent/image.png")
        assert result.steps[0].success is False
        assert result.steps[0].error is not None

    def test_pipeline_debug_saves_intermediates(self, test_image_file, tmp_path):
        from ocr_manga_title.preprocess.pipeline import PreProcessingPipeline

        images_dir = tmp_path / "images"
        images_dir.mkdir()
        config = {
            "preprocessing": {
                "enabled": True,
                "debug": True,
                "grayscale": {"enabled": True},
            }
        }
        pipeline = PreProcessingPipeline(config, images_dir)
        result = pipeline.process(test_image_file)
        debug_dir = images_dir / ".preprocess"
        assert debug_dir.exists()
        assert any(
            s.output_path is not None for s in result.steps if s.enabled and s.success
        )

    def test_pipeline_disabled_step_skipped(self, test_image_file, tmp_path):
        from ocr_manga_title.preprocess.pipeline import PreProcessingPipeline

        config = {
            "preprocessing": {
                "enabled": True,
                "debug": False,
                "grayscale": {"enabled": True},
                "upscale": {"enabled": False, "method": "cubic", "scale_factor": 2},
                "denoise": {"enabled": False, "method": "gaussian"},
                "binarize": {"enabled": True, "method": "otsu"},
            }
        }
        pipeline = PreProcessingPipeline(config, tmp_path)
        result = pipeline.process(test_image_file)
        for step in result.steps:
            if step.step_name in ("upscale", "denoise"):
                assert step.enabled is False
            else:
                assert step.enabled is True

    def test_pipeline_step_execution_order(self, test_image_file, tmp_path):
        from ocr_manga_title.preprocess.pipeline import PreProcessingPipeline

        config = {
            "preprocessing": {
                "enabled": True,
                "debug": False,
                "grayscale": {"enabled": True},
                "denoise": {"enabled": True, "method": "gaussian", "strength": "light"},
                "binarize": {"enabled": True, "method": "otsu"},
            }
        }
        pipeline = PreProcessingPipeline(config, tmp_path)
        result = pipeline.process(test_image_file)
        step_names = [s.step_name for s in result.steps]
        assert step_names.index("grayscale") < step_names.index("binarize")
