import sys
from unittest.mock import MagicMock, patch

import pytest

from ocr_manga_title.engine.easyocr_model import EasyOCRModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult


def _make_config(**params):
    return ModelConfig(name="easyocr", parameters=params)


@pytest.fixture
def mock_easyocr():
    mock_module = MagicMock()
    mock_cls = MagicMock()
    mock_instance = MagicMock()
    mock_cls.return_value = mock_instance
    mock_module.Reader = mock_cls
    with patch.dict(sys.modules, {"easyocr": mock_module}):
        yield mock_cls, mock_instance


class TestEasyOCRModelAvailability:
    @patch("ocr_manga_title.engine.easyocr_model.importlib.util.find_spec")
    def test_is_available_true_when_installed(self, mock_find):
        mock_find.return_value = MagicMock()
        model = EasyOCRModel(_make_config())
        assert model.is_available is True

    @patch("ocr_manga_title.engine.easyocr_model.importlib.util.find_spec")
    def test_is_available_false_when_missing(self, mock_find):
        mock_find.return_value = None
        model = EasyOCRModel(_make_config())
        assert model.is_available is False


class TestEasyOCRModelRun:
    @patch("ocr_manga_title.engine.easyocr_model.importlib.util.find_spec")
    def test_run_raises_when_not_available(self, mock_find):
        mock_find.return_value = None
        model = EasyOCRModel(_make_config())
        with pytest.raises(ModelNotAvailableError):
            model.run("test.png")

    @patch("ocr_manga_title.engine.easyocr_model.importlib.util.find_spec")
    def test_name_returns_easyocr(self, mock_find):
        model = EasyOCRModel(_make_config())
        assert model.name == "easyocr"

    @patch("ocr_manga_title.engine.easyocr_model.importlib.util.find_spec")
    def test_run_returns_ocr_result_with_text(self, mock_find, mock_easyocr):
        mock_find.return_value = MagicMock()
        _, mock_reader = mock_easyocr
        mock_reader.readtext.return_value = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "manga title", 0.92),
        ]

        model = EasyOCRModel(_make_config(languages=["en", "ja"]))
        result = model.run("test.png")

        assert isinstance(result, OCRResult)
        assert result.raw_text == "manga title"
        assert result.confidence == 0.92
        assert result.model_name == "easyocr"
        assert result.processing_time_ms >= 0

    @patch("ocr_manga_title.engine.easyocr_model.importlib.util.find_spec")
    def test_run_returns_empty_on_error(self, mock_find, mock_easyocr):
        mock_find.return_value = MagicMock()
        _, mock_reader = mock_easyocr
        mock_reader.readtext.side_effect = RuntimeError("corrupt image")

        model = EasyOCRModel(_make_config())
        result = model.run("test.png")

        assert result.raw_text == ""
        assert result.confidence == 0.0
        assert "corrupt image" in result.error

    @patch("ocr_manga_title.engine.easyocr_model.importlib.util.find_spec")
    def test_run_returns_empty_for_no_results(self, mock_find, mock_easyocr):
        mock_find.return_value = MagicMock()
        _, mock_reader = mock_easyocr
        mock_reader.readtext.return_value = []

        model = EasyOCRModel(_make_config())
        result = model.run("test.png")

        assert result.raw_text == ""
        assert result.confidence == 0.0

    @patch("ocr_manga_title.engine.easyocr_model.importlib.util.find_spec")
    def test_lazy_load_creates_reader_once(self, mock_find, mock_easyocr):
        mock_find.return_value = MagicMock()
        mock_cls, mock_reader = mock_easyocr
        mock_reader.readtext.return_value = []

        model = EasyOCRModel(_make_config(languages=["ja"]))
        model.run("test1.png")
        model.run("test2.png")

        assert mock_cls.call_count == 1

    @patch("ocr_manga_title.engine.easyocr_model.importlib.util.find_spec")
    def test_reader_uses_configured_languages_and_gpu(self, mock_find, mock_easyocr):
        mock_find.return_value = MagicMock()
        mock_cls, mock_reader = mock_easyocr
        mock_reader.readtext.return_value = []

        model = EasyOCRModel(_make_config(languages=["ja", "en"], gpu=True))
        model.run("test.png")

        args, kwargs = mock_cls.call_args
        assert args[0] == ["ja", "en"]
        assert kwargs["gpu"] is True

    @patch("ocr_manga_title.engine.easyocr_model.importlib.util.find_spec")
    def test_multiple_results_averaged(self, mock_find, mock_easyocr):
        mock_find.return_value = MagicMock()
        _, mock_reader = mock_easyocr
        mock_reader.readtext.return_value = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "line one", 0.8),
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "line two", 0.6),
        ]

        model = EasyOCRModel(_make_config())
        result = model.run("test.png")

        assert result.raw_text == "line one\nline two"
        assert abs(result.confidence - 0.7) < 0.01
