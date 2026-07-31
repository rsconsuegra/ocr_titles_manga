from unittest.mock import MagicMock, patch

import pytest

from ocr_manga_title.exceptions import LLMExtractionError
from ocr_manga_title.postprocess.llm_extractor import LLMExtractor
from ocr_manga_title.schemas import OpenRouterConfig


def _make_config(**kwargs):
    defaults = {
        "api_key": "sk-or-test",
        "default_model": "test-model",
        "base_url": "http://test",
    }
    defaults.update(kwargs)
    return OpenRouterConfig(**defaults)


class TestLLMExtractor:
    @patch("openai.OpenAI")
    def test_llm_extract_valid_response(self, mock_openai_cls):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"title_en": "Naruto", "title_ja": "ナルト", "code": "9780306406157", "confidence": 0.95}'
        mock_response.usage = MagicMock(
            prompt_tokens=10, completion_tokens=20, total_tokens=30
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(), provider="openrouter")
        result = extractor.extract("Naruto text")
        assert result.title_en == "Naruto"
        assert result.title_ja == "ナルト"
        assert result.code == "9780306406157"
        assert result.confidence == 0.95

    @patch("openai.OpenAI")
    def test_llm_extract_null_response(self, mock_openai_cls):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = (
            '{"title_en": null, "title_ja": null, "code": null, "confidence": 0.0}'
        )
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(), provider="openrouter")
        result = extractor.extract("random text")
        assert result.title_en is None
        assert result.confidence == 0.0

    @patch("openai.OpenAI")
    def test_llm_extract_invalid_json(self, mock_openai_cls):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not json at all"
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(), provider="openrouter")
        result = extractor.extract("text")
        assert result.title_en is None
        assert result.confidence == 0.0
        assert result.source_method == "llm_unparsed"

    @patch("openai.OpenAI")
    def test_llm_extract_json_in_markdown(self, mock_openai_cls):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '```json\n{"title_en": "One Piece", "title_ja": null, "code": null, "confidence": 0.8}\n```'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(), provider="openrouter")
        result = extractor.extract("text")
        assert result.title_en == "One Piece"

    @patch("openai.OpenAI")
    def test_llm_extract_api_error(self, mock_openai_cls):
        import openai

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APIError(
            message="err", request=MagicMock(), body=None
        )
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(), provider="openrouter")
        with pytest.raises(LLMExtractionError):
            extractor.extract("text")

    @patch("openai.OpenAI")
    def test_llm_extract_timeout(self, mock_openai_cls):
        import openai

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APITimeoutError(
            request=MagicMock()
        )
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(), provider="openrouter")
        with pytest.raises(LLMExtractionError):
            extractor.extract("text")

    @patch("openai.OpenAI")
    def test_llm_extract_auth_error(self, mock_openai_cls):
        import openai

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
            message="bad key", response=MagicMock(), body=None
        )
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(), provider="openrouter")
        with pytest.raises(LLMExtractionError):
            extractor.extract("text")

    @patch("openai.OpenAI")
    def test_llm_extract_uses_config_model(self, mock_openai_cls):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"title_en": null, "confidence": 0.0}'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(default_model="my-model"), provider="openrouter")
        extractor.extract("text")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "my-model"

    @patch("openai.OpenAI")
    def test_llm_extract_uses_override_model(self, mock_openai_cls):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"title_en": null, "confidence": 0.0}'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(), provider="openrouter")
        extractor.extract("text", model="custom-model")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "custom-model"

    @patch("openai.OpenAI")
    def test_llm_extract_loads_prompt(self, mock_openai_cls, tmp_path):
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text("My custom prompt")
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(), provider="openrouter", prompt_path=str(prompt_file))
        assert extractor._system_prompt == "My custom prompt"

    @patch("openai.OpenAI")
    def test_llm_extract_fallback_prompt(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(), provider="openrouter", prompt_path="/nonexistent/prompt.md")
        assert "manga metadata" in extractor._system_prompt

    @patch("openai.OpenAI")
    def test_llm_extract_temperature(self, mock_openai_cls):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"confidence": 0.0}'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(), provider="openrouter")
        extractor.extract("text")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.1

    @patch("openai.OpenAI")
    def test_llm_extract_logs_token_usage(self, mock_openai_cls, caplog):
        import logging

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"confidence": 0.0}'
        mock_response.usage = MagicMock(
            prompt_tokens=10, completion_tokens=20, total_tokens=30
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        extractor = LLMExtractor(openrouter_config=_make_config(), provider="openrouter")
        with caplog.at_level(logging.DEBUG):
            extractor.extract("text")
        assert "token usage" in caplog.text
