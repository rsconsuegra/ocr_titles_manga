from unittest.mock import MagicMock, patch

import pytest

from ocr_manga_title.engine.glm_ocr_model import GLMOCRModel
from ocr_manga_title.exceptions import ModelNotAvailableError
from ocr_manga_title.schemas import ModelConfig, OCRResult


def _make_config(**params):
    return ModelConfig(name="glm_ocr", parameters=params)


class TestGLMOCRModelAvailability:
    def test_is_available_true_when_endpoint_set(self):
        model = GLMOCRModel(
            _make_config(api_endpoint="https://api.example.com/v1")
        )
        assert model.is_available is True

    def test_is_available_false_when_endpoint_empty(self):
        model = GLMOCRModel(_make_config())
        assert model.is_available is False

    def test_is_available_false_when_endpoint_blank(self):
        model = GLMOCRModel(_make_config(api_endpoint=""))
        assert model.is_available is False


class TestGLMOCRModelRun:
    def test_run_raises_when_not_available(self):
        model = GLMOCRModel(_make_config())
        with pytest.raises(ModelNotAvailableError):
            model.run("test.png")

    def test_name_returns_glm_ocr(self):
        model = GLMOCRModel(_make_config())
        assert model.name == "glm_ocr"

    def test_run_raises_file_not_found(self):
        model = GLMOCRModel(
            _make_config(api_endpoint="https://api.example.com/v1")
        )
        with pytest.raises(FileNotFoundError):
            model.run("/nonexistent_image.png")

    @patch("openai.OpenAI")
    def test_run_sends_base64_image(self, mock_openai_cls, blank_image):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "extracted text"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        model = GLMOCRModel(
            _make_config(api_endpoint="https://api.example.com/v1")
        )
        result = model.run(blank_image)

        assert isinstance(result, OCRResult)
        assert result.raw_text == "extracted text"
        assert result.confidence == 0.8
        assert result.model_name == "glm_ocr"
        assert result.processing_time_ms >= 0

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        content = call_kwargs["messages"][0]["content"]
        image_part = [c for c in content if c["type"] == "image_url"][0]
        assert "data:image/png;base64," in image_part["image_url"]["url"]

    @patch("openai.OpenAI")
    def test_run_handles_api_error(self, mock_openai_cls, blank_image):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API timeout")
        mock_openai_cls.return_value = mock_client

        model = GLMOCRModel(
            _make_config(api_endpoint="https://api.example.com/v1")
        )
        result = model.run(blank_image)

        assert result.raw_text == ""
        assert result.confidence == 0.0
        assert "API timeout" in result.error

    @patch("openai.OpenAI")
    def test_run_handles_rate_limit(self, mock_openai_cls, blank_image):
        import openai

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.RateLimitError(
            "rate limited", response=MagicMock(status_code=429), body=None
        )
        mock_openai_cls.return_value = mock_client

        model = GLMOCRModel(
            _make_config(api_endpoint="https://api.example.com/v1")
        )
        result = model.run(blank_image)

        assert result.raw_text == ""
        assert result.error is not None

    @patch("openai.OpenAI")
    def test_configurable_model_and_prompt(self, mock_openai_cls, blank_image):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "text"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        model = GLMOCRModel(
            _make_config(
                api_endpoint="https://api.example.com/v1",
                model="gpt-4o",
                prompt="Read this",
            )
        )
        model.run(blank_image)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"
        text_parts = [
            c for c in call_kwargs["messages"][0]["content"] if c["type"] == "text"
        ]
        assert text_parts[0]["text"] == "Read this"

    @patch("openai.OpenAI")
    def test_uses_configured_endpoint(self, mock_openai_cls, blank_image):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "text"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        model = GLMOCRModel(
            _make_config(
                api_endpoint="https://custom.api/v1",
                api_key="sk-test",
            )
        )
        model.run(blank_image)

        mock_openai_cls.assert_called_once_with(
            base_url="https://custom.api/v1", api_key="sk-test"
        )

    @patch("openai.OpenAI")
    def test_empty_response_gives_zero_confidence(self, mock_openai_cls, blank_image):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ""
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        model = GLMOCRModel(
            _make_config(api_endpoint="https://api.example.com/v1")
        )
        result = model.run(blank_image)

        assert result.raw_text == ""
        assert result.confidence == 0.0

    @patch("openai.OpenAI")
    def test_handles_jpg_mime_type(self, mock_openai_cls, tmp_path):
        from PIL import Image

        img = Image.new("RGB", (1, 1), "white")
        jpg_path = tmp_path / "test.jpg"
        img.save(jpg_path)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "text"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        model = GLMOCRModel(
            _make_config(api_endpoint="https://api.example.com/v1")
        )
        model.run(str(jpg_path))

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        content = call_kwargs["messages"][0]["content"]
        image_part = [c for c in content if c["type"] == "image_url"][0]
        assert "data:image/jpeg;base64," in image_part["image_url"]["url"]

    @patch("openai.OpenAI")
    def test_client_cached_across_calls(self, mock_openai_cls, blank_image):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "text"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        model = GLMOCRModel(
            _make_config(api_endpoint="https://api.example.com/v1")
        )
        model.run(blank_image)
        model.run(blank_image)

        assert mock_openai_cls.call_count == 1
