from unittest.mock import MagicMock, patch

import pytest

from ocr_manga_title.exceptions import LLMExtractionError
from ocr_manga_title.postprocess.llm_extractor import LLMExtractor
from ocr_manga_title.postprocess.rule_matcher import RuleMatcher
from ocr_manga_title.schemas import ExtractedTitle, OpenRouterConfig


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
        with pytest.raises(LLMExtractionError):
            extractor.extract("text")

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


class TestRuleMatcher:
    def test_match_isbn10_with_prefix(self):
        result = RuleMatcher().match("ISBN 0-306-40615-2")
        assert result.code == "0306406152"

    def test_match_isbn10_without_prefix(self):
        result = RuleMatcher().match("0-306-40615-2")
        assert result.code == "0306406152"

    def test_match_isbn10_with_x(self):
        result = RuleMatcher().match("0-8044-2957-X")
        assert result.code == "080442957X"

    def test_match_isbn13_with_prefix(self):
        result = RuleMatcher().match("ISBN 978-0-306-40615-7")
        assert result.code == "9780306406157"

    def test_match_isbn13_without_prefix(self):
        result = RuleMatcher().match("9780306406157")
        assert result.code == "9780306406157"

    def test_match_isbn13_preferred_over_isbn10(self):
        text = "ISBN 0-306-40615-2 and ISBN 978-0-306-40615-7"
        result = RuleMatcher().match(text)
        assert result.code == "9780306406157"

    def test_match_no_code(self):
        result = RuleMatcher().match("just some text")
        assert result.code is None
        assert result.confidence == 0.0

    def test_match_code_in_longer_text(self):
        result = RuleMatcher().match("Published as ISBN 0-306-40615-2 in Japan")
        assert result.code == "0306406152"

    def test_match_rejects_invalid_isbn10_checksum(self):
        result = RuleMatcher().match("0-306-40615-9")
        assert result.code is None

    def test_match_rejects_invalid_isbn13_checksum(self):
        result = RuleMatcher().match("9780306406150")
        assert result.code is None

    def test_normalize_title_whitespace(self):
        assert RuleMatcher.normalize_title("  Hello   World  ") == "Hello World"

    def test_normalize_title_trailing_punctuation(self):
        assert RuleMatcher.normalize_title("One Piece！！") == "One Piece"

    def test_normalize_title_unicode_nfc(self):
        import unicodedata

        decomposed = "e\u0301"
        normalized = RuleMatcher.normalize_title(decomposed)
        assert unicodedata.is_normalized("NFC", normalized)

    def test_normalize_isbn_strips_hyphens(self):
        assert RuleMatcher.normalize_isbn("978-0-306-40615-7") == "9780306406157"

    def test_normalize_isbn_strips_prefix(self):
        assert RuleMatcher.normalize_isbn("ISBN 978-0-306-40615-7") == "9780306406157"

    def test_augment_fills_missing_code(self):
        existing = ExtractedTitle(
            title_en="Naruto", code=None, confidence=0.8, source_method="llm"
        )
        result = RuleMatcher().augment(existing, "ISBN 978-0-306-40615-7")
        assert result.code == "9780306406157"
        assert result.source_method == "llm+rules"

    def test_augment_does_not_overwrite_code(self):
        existing = ExtractedTitle(code="existing", confidence=0.8, source_method="llm")
        result = RuleMatcher().augment(existing, "ISBN 978-0-306-40615-7")
        assert result.code == "existing"

    def test_augment_normalizes_existing_titles(self):
        existing = ExtractedTitle(
            title_en="  Naruto  !", confidence=0.8, source_method="llm"
        )
        result = RuleMatcher().augment(existing, "no codes here")
        assert result.title_en == "Naruto"

    def test_augment_source_method(self):
        existing = ExtractedTitle(confidence=0.0, source_method="rules")
        result = RuleMatcher().augment(existing, "ISBN 978-0-306-40615-7")
        assert result.code == "9780306406157"
        assert result.source_method == "rules"

    def test_augment_no_changes(self):
        existing = ExtractedTitle(
            title_en="Naruto",
            title_ja="ナルト",
            code="1234",
            confidence=0.9,
            source_method="llm",
        )
        result = RuleMatcher().augment(existing, "no codes here")
        assert result.code == "1234"
        assert result.title_en == "Naruto"
