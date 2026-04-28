import pytest

from ocr_manga_title.exceptions import ConfigurationError
from ocr_manga_title.schemas import (
    AppConfig,
    ExtractedTitle,
    ModelConfig,
    OCRResult,
    OpenRouterConfig,
    PipelineResult,
)


class TestOCRResult:
    def test_ocr_result_valid(self):
        r = OCRResult(
            raw_text="hello", model_name="test", confidence=0.8, processing_time_ms=100
        )
        assert r.raw_text == "hello"
        assert r.model_name == "test"
        assert r.confidence == 0.8
        assert r.error is None

    def test_ocr_result_minimal(self):
        r = OCRResult(model_name="test")
        assert r.raw_text == ""
        assert r.confidence == 0.0
        assert r.processing_time_ms == 0
        assert r.error is None


class TestExtractedTitle:
    def test_extracted_title_all_none(self):
        t = ExtractedTitle()
        assert t.title_en is None
        assert t.title_ja is None
        assert t.code is None
        assert t.confidence == 0.0

    def test_extracted_title_all_populated(self):
        t = ExtractedTitle(
            title_en="Naruto", title_ja="ナルト", code="1234", confidence=0.95
        )
        assert t.title_en == "Naruto"
        assert t.title_ja == "ナルト"


class TestPipelineResult:
    def test_pipeline_result_serialization(self):
        r = PipelineResult(input_path="/test.png")
        json_str = r.model_dump_json()
        assert "/test.png" in json_str

    def test_pipeline_result_deserialization(self):
        data = {"input_path": "/test.png", "ocr_results": [], "errors": []}
        r = PipelineResult(**data)
        assert r.input_path == "/test.png"


class TestAppConfig:
    def test_app_config_missing_openrouter(self):
        with pytest.raises(Exception):
            AppConfig()

    def test_openrouter_config_api_key_validation(self):
        with pytest.raises(ConfigurationError, match="sk-"):
            OpenRouterConfig(api_key="bad-key")


class TestModelConfig:
    def test_model_config_defaults(self):
        mc = ModelConfig(name="test")
        assert mc.enabled is True
        assert mc.parameters == {}

    def test_model_config_extract_name_from_key(self):
        mc = ModelConfig(__key__="tesseract", enabled=True)
        assert mc.name == "tesseract"
