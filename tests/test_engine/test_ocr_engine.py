from unittest.mock import MagicMock, patch

import pytest

from ocr_manga_title.engine import OCREngine
from ocr_manga_title.schemas import (
    AppConfig,
    ExtractedTitle,
    ModelConfig,
    OCRResult,
    OpenRouterConfig,
    PreProcessStepResult,
)


def _make_engine(
    tmp_path, models_config=None, mock_models=True, preprocess_config=None
):
    images_dir = tmp_path / "images"
    images_dir.mkdir(exist_ok=True)
    config = AppConfig(
        images_path=images_dir,
        openrouter=OpenRouterConfig(
            api_key="sk-or-test", default_model="test-model", base_url="http://test"
        ),
    )
    if models_config is None:
        models_config = {
            "tesseract": ModelConfig(
                name="tesseract", enabled=True, parameters={"languages": ["eng", "jpn"]}
            ),
        }
    return OCREngine(config, models_config, preprocess_config)


class TestOCREngineInit:
    def test_engine_initializes_enabled_available_models(self, tmp_path):
        with patch(
            "ocr_manga_title.engine.tesseract_model.TesseractModel.is_available", True
        ):
            engine = _make_engine(tmp_path)
            assert len(engine._models) == 1

    def test_engine_skips_disabled_models(self, tmp_path):
        models_config = {
            "tesseract": ModelConfig(
                name="tesseract", enabled=False, parameters={"languages": ["eng"]}
            ),
        }
        engine = _make_engine(tmp_path, models_config=models_config)
        assert len(engine._models) == 0

    def test_engine_skips_unavailable_models(self, tmp_path):
        with patch(
            "ocr_manga_title.engine.tesseract_model.TesseractModel.is_available", False
        ):
            engine = _make_engine(tmp_path)
            assert len(engine._models) == 0

    def test_engine_skips_unavailable_stubs(self, tmp_path):
        models_config = {
            "paddle": ModelConfig(name="paddle", enabled=True),
        }
        engine = _make_engine(tmp_path, models_config=models_config)
        assert len(engine._models) == 0

    def test_engine_no_models_available_logs_warning(self, tmp_path, caplog):
        import logging

        models_config = {
            "tesseract": ModelConfig(name="tesseract", enabled=False),
        }
        with caplog.at_level(logging.WARNING):
            _make_engine(tmp_path, models_config=models_config)
        assert "No OCR models available" in caplog.text

    def test_engine_unknown_model_name_warning(self, tmp_path, caplog):
        import logging

        models_config = {
            "unknown_model": ModelConfig(name="unknown_model", enabled=True),
        }
        with caplog.at_level(logging.WARNING):
            _make_engine(tmp_path, models_config=models_config)
        assert "Unknown model" in caplog.text

    def test_engine_all_stubs_skipped(self, tmp_path):
        models_config = {
            "paddle": ModelConfig(name="paddle", enabled=True),
            "easyocr": ModelConfig(name="easyocr", enabled=True),
        }
        engine = _make_engine(tmp_path, models_config=models_config)
        assert len(engine._models) == 0


class TestOCREngineProcess:
    def _make_engine_with_mocks(self, tmp_path, mock_results=None):
        engine = _make_engine(tmp_path)
        if mock_results is None:
            mock_results = [
                OCRResult(
                    raw_text="One Piece",
                    model_name="tesseract",
                    confidence=0.6,
                    processing_time_ms=50,
                ),
            ]
        engine._models = []
        for r in mock_results:
            m = MagicMock()
            m.name = r.model_name
            m.run.return_value = r
            engine._models.append(m)
        return engine

    @patch("openai.OpenAI")
    def test_process_returns_pipeline_result(
        self, mock_openai_cls, tmp_path, blank_image
    ):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"title_en": "One Piece", "confidence": 0.9}'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        engine = self._make_engine_with_mocks(tmp_path)
        result = engine.process(blank_image)
        assert result.input_path == blank_image
        assert len(result.ocr_results) == 1
        assert result.extracted is not None

    @patch("openai.OpenAI")
    def test_process_runs_all_enabled_models(
        self, mock_openai_cls, tmp_path, blank_image
    ):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"confidence": 0.0}'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        engine = self._make_engine_with_mocks(tmp_path)
        result = engine.process(blank_image)
        assert len(result.ocr_results) == 1
        for m in engine._models:
            m.run.assert_called_once()

    @patch("openai.OpenAI")
    def test_process_one_model_fails_other_succeeds(
        self, mock_openai_cls, tmp_path, blank_image
    ):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"title_en": "test", "confidence": 0.8}'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        engine = self._make_engine_with_mocks(tmp_path)
        engine._models[0].run.side_effect = RuntimeError("model crashed")
        result = engine.process(blank_image)
        assert len(result.ocr_results) == 1
        assert result.ocr_results[0].error is not None

    @patch("openai.OpenAI")
    def test_process_all_models_fail(self, mock_openai_cls, tmp_path, blank_image):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        engine = self._make_engine_with_mocks(tmp_path)
        for m in engine._models:
            m.run.side_effect = RuntimeError("fail")
        result = engine.process(blank_image)
        assert len(result.errors) == 1

    @patch("openai.OpenAI")
    def test_process_llm_fails_rules_succeed(
        self, mock_openai_cls, tmp_path, blank_image
    ):
        import openai

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APIError(
            message="err", request=MagicMock(), body=None
        )
        mock_openai_cls.return_value = mock_client

        results = [
            OCRResult(
                raw_text="ISBN 978-0-306-40615-7 some text",
                model_name="tesseract",
                confidence=0.7,
                processing_time_ms=100,
            ),
        ]
        engine = self._make_engine_with_mocks(tmp_path, mock_results=results)
        result = engine.process(blank_image)
        assert result.extracted is not None
        assert "9780306406157" in result.extracted.code

    @patch("openai.OpenAI")
    def test_process_llm_and_rules_both_fail(
        self, mock_openai_cls, tmp_path, blank_image
    ):
        import openai

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APIError(
            message="err", request=MagicMock(), body=None
        )
        mock_openai_cls.return_value = mock_client

        results = [
            OCRResult(
                raw_text="no codes here",
                model_name="tesseract",
                confidence=0.7,
                processing_time_ms=100,
            ),
        ]
        engine = self._make_engine_with_mocks(tmp_path, mock_results=results)
        result = engine.process(blank_image)
        assert result.extracted is None

    def test_process_missing_image_raises_file_not_found(self, tmp_path):
        engine = _make_engine(tmp_path)
        with pytest.raises(FileNotFoundError):
            engine.process("/nonexistent.png")

    def test_process_unsupported_format_raises_value_error(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not an image")
        engine = _make_engine(tmp_path)
        with pytest.raises(ValueError, match="Unsupported"):
            engine.process(str(txt_file))

    @patch("ocr_manga_title.engine.ocr_engine.LLMExtractor")
    @patch("ocr_manga_title.engine.ocr_engine.RuleMatcher")
    def test_process_runs_llm_on_each_result(
        self, mock_rule_cls, mock_llm_cls, tmp_path, blank_image
    ):
        mock_llm = MagicMock()
        mock_llm.extract.return_value = ExtractedTitle(confidence=0.5)
        mock_llm_cls.return_value = mock_llm
        mock_rule = MagicMock()
        mock_rule.augment.side_effect = lambda e, t: e
        mock_rule_cls.return_value = mock_rule

        results = [
            OCRResult(
                raw_text="text1",
                model_name="tesseract",
                confidence=0.6,
                processing_time_ms=50,
            ),
        ]
        engine = self._make_engine_with_mocks(tmp_path, mock_results=results)
        engine.process(blank_image)
        assert mock_llm.extract.call_count == 1

    @patch("ocr_manga_title.engine.ocr_engine.LLMExtractor")
    @patch("ocr_manga_title.engine.ocr_engine.RuleMatcher")
    def test_process_runs_rules_on_each_result(
        self, mock_rule_cls, mock_llm_cls, tmp_path, blank_image
    ):
        mock_llm = MagicMock()
        mock_llm.extract.return_value = ExtractedTitle(confidence=0.5)
        mock_llm_cls.return_value = mock_llm
        mock_rule = MagicMock()
        mock_rule.augment.side_effect = lambda e, t: e
        mock_rule_cls.return_value = mock_rule

        results = [
            OCRResult(
                raw_text="text1",
                model_name="tesseract",
                confidence=0.6,
                processing_time_ms=50,
            ),
        ]
        engine = self._make_engine_with_mocks(tmp_path, mock_results=results)
        engine.process(blank_image)
        assert mock_rule.augment.call_count == 1

    @patch("openai.OpenAI")
    def test_process_no_text_extracted(self, mock_openai_cls, tmp_path, blank_image):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"confidence": 0.0}'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        results = [
            OCRResult(
                raw_text="",
                model_name="tesseract",
                confidence=0.0,
                processing_time_ms=100,
            ),
        ]
        engine = self._make_engine_with_mocks(tmp_path, mock_results=results)
        result = engine.process(blank_image)
        assert result.extracted is None

    @patch("openai.OpenAI")
    def test_process_single_model(self, mock_openai_cls, tmp_path, blank_image):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"title_en": "Solo", "confidence": 0.8}'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        results = [
            OCRResult(
                raw_text="text",
                model_name="tesseract",
                confidence=0.7,
                processing_time_ms=100,
            ),
        ]
        engine = self._make_engine_with_mocks(tmp_path, mock_results=results)
        result = engine.process(blank_image)
        assert len(result.ocr_results) == 1
        assert result.ocr_results[0].model_name == "tesseract"

    @patch("openai.OpenAI")
    def test_process_selects_best_confidence(
        self, mock_openai_cls, tmp_path, blank_image
    ):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.usage = None

        call_count = [0]

        def side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                mock_response.choices[
                    0
                ].message.content = '{"title_en": "Low", "confidence": 0.3}'
            else:
                mock_response.choices[
                    0
                ].message.content = '{"title_en": "High", "confidence": 0.9}'
            return mock_response

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = side_effect
        mock_openai_cls.return_value = mock_client

        results = [
            OCRResult(
                raw_text="text1",
                model_name="tesseract",
                confidence=0.6,
                processing_time_ms=50,
            ),
            OCRResult(
                raw_text="text2",
                model_name="tesseract2",
                confidence=0.7,
                processing_time_ms=100,
            ),
        ]
        engine = self._make_engine_with_mocks(tmp_path, mock_results=results)
        result = engine.process(blank_image)
        assert result.extracted.title_en == "High"


class TestOCREnginePreprocessing:
    @patch("openai.OpenAI")
    def test_process_with_preprocessing_enabled(
        self, mock_openai_cls, tmp_path, blank_image
    ):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"title_en": "Test", "confidence": 0.8}'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        preprocess_config = {
            "preprocessing": {
                "enabled": True,
                "debug": False,
                "grayscale": {"enabled": True},
                "binarize": {"enabled": True, "method": "otsu"},
            }
        }

        with patch(
            "ocr_manga_title.engine.tesseract_model.TesseractModel.is_available", True
        ):
            engine = _make_engine(tmp_path, preprocess_config=preprocess_config)

        engine._models = []
        mock_model = MagicMock()
        mock_model.name = "test-model"
        mock_model.run.return_value = OCRResult(
            raw_text="test",
            model_name="test-model",
            confidence=0.7,
            processing_time_ms=10,
        )
        engine._models.append(mock_model)

        result = engine.process(blank_image)
        assert result.preprocess_result is not None
        assert len(result.preprocess_result.steps) > 0

    @patch("openai.OpenAI")
    def test_process_with_preprocessing_disabled(
        self, mock_openai_cls, tmp_path, blank_image
    ):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"title_en": "Test", "confidence": 0.8}'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        with patch(
            "ocr_manga_title.engine.tesseract_model.TesseractModel.is_available", True
        ):
            engine = _make_engine(tmp_path)

        engine._models = []
        mock_model = MagicMock()
        mock_model.name = "test-model"
        mock_model.run.return_value = OCRResult(
            raw_text="test",
            model_name="test-model",
            confidence=0.7,
            processing_time_ms=10,
        )
        engine._models.append(mock_model)

        result = engine.process(blank_image)
        assert result.preprocess_result is None

    @patch("openai.OpenAI")
    def test_process_preprocessing_failure_fallback(
        self, mock_openai_cls, tmp_path, blank_image
    ):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"title_en": "Test", "confidence": 0.8}'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        preprocess_config = {
            "preprocessing": {
                "enabled": True,
                "debug": False,
                "grayscale": {"enabled": True},
            }
        }

        with patch(
            "ocr_manga_title.engine.tesseract_model.TesseractModel.is_available", True
        ):
            engine = _make_engine(tmp_path, preprocess_config=preprocess_config)

        engine._models = []
        mock_model = MagicMock()
        mock_model.name = "test-model"
        mock_model.run.return_value = OCRResult(
            raw_text="test",
            model_name="test-model",
            confidence=0.7,
            processing_time_ms=10,
        )
        engine._models.append(mock_model)

        from unittest.mock import patch as ut_patch

        from ocr_manga_title.schemas import PreProcessResult

        with ut_patch.object(
            engine._preprocess_pipeline,
            "process",
            return_value=PreProcessResult(
                input_path=blank_image,
                output_path=None,
                steps=[
                    PreProcessStepResult(
                        step_name="load",
                        enabled=True,
                        success=False,
                        processing_time_ms=0,
                        error="bad image",
                    )
                ],
            ),
        ):
            result = engine.process(blank_image)

        assert result.preprocess_result is not None
        mock_model.run.assert_called_once_with(blank_image)

    @patch("openai.OpenAI")
    def test_process_preprocessing_provides_image_to_ocr(
        self, mock_openai_cls, tmp_path, blank_image
    ):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"title_en": "Test", "confidence": 0.8}'
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        preprocess_config = {
            "preprocessing": {
                "enabled": True,
                "debug": True,
                "grayscale": {"enabled": True},
            }
        }

        with patch(
            "ocr_manga_title.engine.tesseract_model.TesseractModel.is_available", True
        ):
            engine = _make_engine(tmp_path, preprocess_config=preprocess_config)

        engine._models = []
        mock_model = MagicMock()
        mock_model.name = "test-model"
        mock_model.run.return_value = OCRResult(
            raw_text="test",
            model_name="test-model",
            confidence=0.7,
            processing_time_ms=10,
        )
        engine._models.append(mock_model)

        engine.process(blank_image)
        call_arg = mock_model.run.call_args[0][0]
        assert call_arg != blank_image
        assert ".preprocess" in call_arg

    def test_engine_backward_compat_no_preprocess_config(self, tmp_path):
        with patch(
            "ocr_manga_title.engine.tesseract_model.TesseractModel.is_available", True
        ):
            engine = _make_engine(tmp_path)
        assert engine._preprocess_pipeline is None
