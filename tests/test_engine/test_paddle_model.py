import sys
from unittest.mock import MagicMock, patch

import pytest

from ocr_manga_title.engine.paddle_model import PaddleModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult


def _make_config(**params):
    return ModelConfig(name="paddle", parameters=params)


@pytest.fixture
def mock_paddleocr():
    mock_module = MagicMock()
    mock_cls = MagicMock()
    mock_instance = MagicMock()
    mock_cls.return_value = mock_instance
    mock_module.PaddleOCR = mock_cls
    with patch.dict(sys.modules, {"paddleocr": mock_module}):
        yield mock_cls, mock_instance


class TestPaddleModelAvailability:
    @patch("ocr_manga_title.engine.paddle_model.importlib.util.find_spec")
    def test_is_available_true_when_installed(self, mock_find):
        mock_find.return_value = MagicMock()
        model = PaddleModel(_make_config())
        assert model.is_available is True

    @patch("ocr_manga_title.engine.paddle_model.importlib.util.find_spec")
    def test_is_available_false_when_missing(self, mock_find):
        mock_find.return_value = None
        model = PaddleModel(_make_config())
        assert model.is_available is False


class TestPaddleModelRun:
    @patch("ocr_manga_title.engine.paddle_model.importlib.util.find_spec")
    def test_run_raises_when_not_available(self, mock_find):
        mock_find.return_value = None
        model = PaddleModel(_make_config())
        with pytest.raises(ModelNotAvailableError):
            model.run("test.png")

    @patch("ocr_manga_title.engine.paddle_model.importlib.util.find_spec")
    def test_name_returns_paddle(self, mock_find):
        model = PaddleModel(_make_config())
        assert model.name == "paddle"

    @patch("ocr_manga_title.engine.paddle_model.importlib.util.find_spec")
    def test_run_returns_ocr_result_with_text(self, mock_find, mock_paddleocr):
        mock_find.return_value = MagicMock()
        mock_cls, mock_instance = mock_paddleocr
        mock_instance.ocr.return_value = [
            [
                [
                    [[10.0, 20.0], [100.0, 20.0], [100.0, 50.0], [10.0, 50.0]],
                    ("hello world", 0.95),
                ]
            ]
        ]

        model = PaddleModel(_make_config(languages=["en", "ja"]))
        result = model.run("test.png")

        assert isinstance(result, OCRResult)
        assert result.raw_text == "hello world"
        assert result.confidence == 0.95
        assert result.model_name == "paddle"
        assert result.processing_time_ms >= 0

    @patch("ocr_manga_title.engine.paddle_model.importlib.util.find_spec")
    def test_run_returns_empty_on_error(self, mock_find, mock_paddleocr):
        mock_find.return_value = MagicMock()
        _, mock_instance = mock_paddleocr
        mock_instance.ocr.side_effect = RuntimeError("corrupt image")

        model = PaddleModel(_make_config())
        result = model.run("test.png")

        assert result.raw_text == ""
        assert result.confidence == 0.0
        assert "corrupt image" in result.error

    @patch("ocr_manga_title.engine.paddle_model.importlib.util.find_spec")
    def test_run_returns_empty_for_null_result(self, mock_find, mock_paddleocr):
        mock_find.return_value = MagicMock()
        _, mock_instance = mock_paddleocr
        mock_instance.ocr.return_value = None

        model = PaddleModel(_make_config())
        result = model.run("test.png")

        assert result.raw_text == ""
        assert result.confidence == 0.0

    @patch("ocr_manga_title.engine.paddle_model.importlib.util.find_spec")
    def test_lazy_load_creates_model_once(self, mock_find, mock_paddleocr):
        mock_find.return_value = MagicMock()
        mock_cls, mock_instance = mock_paddleocr
        mock_instance.ocr.return_value = None

        model = PaddleModel(_make_config(languages=["ja"]))
        model.run("test1.png")
        model.run("test2.png")

        assert mock_cls.call_count == 1

    @patch("ocr_manga_title.engine.paddle_model.importlib.util.find_spec")
    def test_configurable_language_and_gpu(self, mock_find, mock_paddleocr):
        mock_find.return_value = MagicMock()
        mock_cls, mock_instance = mock_paddleocr
        mock_instance.ocr.return_value = None

        model = PaddleModel(_make_config(languages=["ja"], use_gpu=True))
        model.run("test.png")

        _, kwargs = mock_cls.call_args
        assert kwargs["lang"] == "japan"
        assert kwargs["use_gpu"] is True

    @patch("ocr_manga_title.engine.paddle_model.importlib.util.find_spec")
    def test_gpu_fallback_to_cpu(self, mock_find, mock_paddleocr):
        mock_find.return_value = MagicMock()
        mock_cls, mock_instance = mock_paddleocr
        mock_instance.ocr.return_value = None

        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("use_gpu"):
                raise RuntimeError("CUDA not available")
            return mock_instance

        mock_cls.side_effect = side_effect

        model = PaddleModel(_make_config(languages=["en"], use_gpu=True))
        result = model.run("test.png")

        assert call_count == 2
        assert result.model_name == "paddle"

    @patch("ocr_manga_title.engine.paddle_model.importlib.util.find_spec")
    def test_multiple_pages_and_lines(self, mock_find, mock_paddleocr):
        mock_find.return_value = MagicMock()
        _, mock_instance = mock_paddleocr
        mock_instance.ocr.return_value = [
            [
                [[[0, 0], [10, 0], [10, 10], [0, 10]], ("page1 line1", 0.9)],
                [[[0, 0], [10, 0], [10, 10], [0, 10]], ("page1 line2", 0.8)],
            ],
            [
                [[[0, 0], [10, 0], [10, 10], [0, 10]], ("page2 line1", 0.7)],
            ],
        ]

        model = PaddleModel(_make_config())
        result = model.run("test.png")

        assert result.raw_text == "page1 line1\npage1 line2\npage2 line1"
        assert abs(result.confidence - 0.8) < 0.01
