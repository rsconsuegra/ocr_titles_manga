from unittest.mock import patch

import pytest

from ocr_manga_title.engine.easyocr_model import EasyOCRModel
from ocr_manga_title.engine.glm_ocr_model import GLMOCRModel
from ocr_manga_title.engine.paddle_model import PaddleModel
from ocr_manga_title.engine.tesseract_model import TesseractModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult


class TestTesseractModel:
    def test_tesseract_name(self):
        config = ModelConfig(
            name="tesseract",
            parameters={"languages": ["eng", "jpn"], "psm": 3, "oem": 3},
        )
        model = TesseractModel(config)
        assert model.name == "tesseract"

    @patch("pytesseract.get_tesseract_version")
    def test_tesseract_is_available_when_installed(self, mock_ver):
        mock_ver.return_value = "5.0"
        config = ModelConfig(name="tesseract", parameters={"languages": ["eng", "jpn"]})
        model = TesseractModel(config)
        assert model.is_available is True

    @patch("pytesseract.get_tesseract_version", side_effect=Exception("not found"))
    def test_tesseract_is_available_when_not_installed(self, mock_ver):
        config = ModelConfig(name="tesseract", parameters={"languages": ["eng", "jpn"]})
        model = TesseractModel(config)
        assert model.is_available is False

    @patch("pytesseract.image_to_data")
    @patch("pytesseract.get_tesseract_version")
    def test_tesseract_run_returns_ocr_result(self, mock_ver, mock_itd, blank_image):
        mock_ver.return_value = "5.0"
        mock_itd.return_value = {
            "text": ["Hello", "World"],
            "conf": ["90", "85"],
        }
        config = ModelConfig(
            name="tesseract",
            parameters={"languages": ["eng", "jpn"], "psm": 3, "oem": 3},
        )
        model = TesseractModel(config)
        result = model.run(blank_image)
        assert isinstance(result, OCRResult)
        assert result.raw_text == "Hello World"

    @patch("pytesseract.image_to_data")
    @patch("pytesseract.get_tesseract_version")
    def test_tesseract_run_uses_language_config(self, mock_ver, mock_itd, blank_image):
        mock_ver.return_value = "5.0"
        mock_itd.return_value = {"text": ["text"], "conf": [95]}
        config = ModelConfig(name="tesseract", parameters={"languages": ["eng", "jpn"]})
        model = TesseractModel(config)
        model.run(blank_image)
        _, kwargs = mock_itd.call_args
        assert kwargs["lang"] == "eng+jpn"

    @patch("pytesseract.image_to_data")
    @patch("pytesseract.get_tesseract_version")
    def test_tesseract_confidence_from_word_data(self, mock_ver, mock_itd, blank_image):
        mock_ver.return_value = "5.0"
        mock_itd.return_value = {"text": ["a", "b", "c"], "conf": ["80", "90", "100"]}
        config = ModelConfig(name="tesseract", parameters={"languages": ["eng"]})
        model = TesseractModel(config)
        result = model.run(blank_image)
        assert abs(result.confidence - 0.9) < 0.01

    @patch("pytesseract.image_to_data")
    @patch("pytesseract.get_tesseract_version")
    def test_tesseract_confidence_filters_low_words(
        self, mock_ver, mock_itd, blank_image
    ):
        mock_ver.return_value = "5.0"
        mock_itd.return_value = {"text": ["a", "b", "c"], "conf": ["10", "20", "90"]}
        config = ModelConfig(name="tesseract", parameters={"languages": ["eng"]})
        model = TesseractModel(config)
        result = model.run(blank_image)
        assert result.confidence == 0.9

    @patch("pytesseract.image_to_data")
    @patch("pytesseract.get_tesseract_version")
    def test_tesseract_confidence_zero_when_no_words(
        self, mock_ver, mock_itd, blank_image
    ):
        mock_ver.return_value = "5.0"
        mock_itd.return_value = {"text": [], "conf": []}
        config = ModelConfig(name="tesseract", parameters={"languages": ["eng"]})
        model = TesseractModel(config)
        result = model.run(blank_image)
        assert result.confidence == 0.0

    def test_tesseract_run_nonexistent_image_raises(self):
        config = ModelConfig(name="tesseract", parameters={"languages": ["eng"]})
        model = TesseractModel(config)
        with pytest.raises(FileNotFoundError):
            model.run("/nonexistent.png")

    @patch("pytesseract.image_to_data")
    @patch("pytesseract.get_tesseract_version")
    def test_tesseract_run_records_processing_time(
        self, mock_ver, mock_itd, blank_image
    ):
        mock_ver.return_value = "5.0"
        mock_itd.return_value = {"text": [], "conf": []}
        config = ModelConfig(name="tesseract", parameters={"languages": ["eng"]})
        model = TesseractModel(config)
        result = model.run(blank_image)
        assert result.processing_time_ms >= 0

    def test_tesseract_language_string_format(self):
        config = ModelConfig(name="tesseract", parameters={"languages": ["eng"]})
        model = TesseractModel(config)
        assert model._lang_string == "eng"

    @patch("pytesseract.get_tesseract_version")
    def test_tesseract_psm_config(self, mock_ver):
        mock_ver.return_value = "5.0"
        config = ModelConfig(
            name="tesseract", parameters={"languages": ["eng"], "psm": 6, "oem": 1}
        )
        model = TesseractModel(config)
        assert "--psm 6" in model._tess_config
        assert "--oem 1" in model._tess_config


class TestPaddleBasic:
    def test_paddle_name(self):
        model = PaddleModel(ModelConfig(name="paddle"))
        assert model.name == "paddle"

    def test_paddle_not_available_without_package(self):
        model = PaddleModel(ModelConfig(name="paddle"))
        assert model.is_available is False

    def test_paddle_run_raises_when_not_available(self):
        model = PaddleModel(ModelConfig(name="paddle"))
        with pytest.raises(ModelNotAvailableError):
            model.run("test.png")


class TestEasyOCRBasic:
    def test_easyocr_name(self):
        model = EasyOCRModel(ModelConfig(name="easyocr"))
        assert model.name == "easyocr"

    def test_easyocr_not_available_without_package(self):
        model = EasyOCRModel(ModelConfig(name="easyocr"))
        assert model.is_available is False

    def test_easyocr_run_raises_when_not_available(self):
        model = EasyOCRModel(ModelConfig(name="easyocr"))
        with pytest.raises(ModelNotAvailableError):
            model.run("test.png")


class TestGLMOCRBasic:
    def test_glm_ocr_name(self):
        model = GLMOCRModel(ModelConfig(name="glm_ocr"))
        assert model.name == "glm_ocr"

    def test_glm_ocr_not_available_without_endpoint(self):
        model = GLMOCRModel(ModelConfig(name="glm_ocr"))
        assert model.is_available is False

    def test_glm_ocr_run_raises_when_not_available(self):
        model = GLMOCRModel(ModelConfig(name="glm_ocr"))
        with pytest.raises(ModelNotAvailableError):
            model.run("test.png")
