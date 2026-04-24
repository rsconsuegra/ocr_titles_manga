from pathlib import Path

import pytest
from pydantic import ValidationError

from ocr_manga_title.config import load_config, load_ocr_config
from ocr_manga_title.exceptions import ConfigurationError
from ocr_manga_title.schemas import ModelConfig


class TestLoadConfig:
    def test_load_valid_config(self, valid_configs_toml):
        config = load_config(valid_configs_toml)
        assert config.images_path.exists()
        assert config.openrouter.api_key.get_secret_value() == "sk-or-test-key-12345"
        assert config.openrouter.default_model == "google/gemini-2.5-flash"

    def test_load_config_missing_file(self, tmp_path):
        with pytest.raises(ConfigurationError, match="not found"):
            load_config(tmp_path / "nonexistent.toml")

    def test_load_config_empty_file(self, tmp_path):
        f = tmp_path / "empty.toml"
        f.write_text("")
        with pytest.raises(ConfigurationError, match="empty"):
            load_config(f)

    def test_load_config_missing_openrouter(self, tmp_path):
        f = tmp_path / "no_openrouter.toml"
        f.write_text('images_path = "/tmp"')
        with pytest.raises(ConfigurationError):
            load_config(f)

    def test_load_config_missing_api_key(self, tmp_path):
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        f = tmp_path / "no_key.toml"
        f.write_text(f'''
images_path = "{images_dir}"

[openrouter]
default_model = "google/gemini-2.5-flash"
''')
        with pytest.raises(ConfigurationError):
            load_config(f)

    def test_load_config_invalid_api_key(self, tmp_path):
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        f = tmp_path / "bad_key.toml"
        f.write_text(f'''
images_path = "{images_dir}"

[openrouter]
api_key = "invalid-key"
''')
        with pytest.raises(ConfigurationError, match="sk-"):
            load_config(f)

    def test_load_config_missing_images_path(self, tmp_path):
        f = tmp_path / "no_path.toml"
        f.write_text("""
[openrouter]
api_key = "sk-or-test"
""")
        with pytest.raises(ConfigurationError):
            load_config(f)

    def test_load_config_nonexistent_images_path_warns(self, tmp_path, caplog):
        import logging

        f = tmp_path / "warn_path.toml"
        f.write_text("""
images_path = "/nonexistent/path/xyz"

[openrouter]
api_key = "sk-or-test"
""")
        with caplog.at_level(logging.WARNING):
            config = load_config(f)
        assert "does not exist" in caplog.text
        assert config.images_path == Path("/nonexistent/path/xyz")

    def test_load_config_default_base_url(self, tmp_path):
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        f = tmp_path / "minimal.toml"
        f.write_text(f'''
images_path = "{images_dir}"

[openrouter]
api_key = "sk-or-test"
''')
        config = load_config(f)
        assert config.openrouter.base_url == "https://openrouter.ai/api/v1"

    def test_load_config_default_model(self, tmp_path):
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        f = tmp_path / "minimal.toml"
        f.write_text(f'''
images_path = "{images_dir}"

[openrouter]
api_key = "sk-or-test"
''')
        config = load_config(f)
        assert config.openrouter.default_model == "google/gemini-2.5-flash"


class TestLoadOCRConfig:
    def test_load_valid_ocr_config(self, valid_ocrs_yaml):
        config = load_ocr_config(valid_ocrs_yaml)
        assert len(config) == 4
        assert "tesseract" in config
        assert config["tesseract"].enabled is True

    def test_load_ocr_config_missing_file(self, tmp_path):
        with pytest.raises(ConfigurationError, match="not found"):
            load_ocr_config(tmp_path / "nonexistent.yaml")

    def test_load_ocr_config_missing_models_key(self, tmp_path):
        f = tmp_path / "no_models.yaml"
        f.write_text("something_else: true")
        with pytest.raises(ConfigurationError, match="models"):
            load_ocr_config(f)

    def test_load_ocr_config_default_enabled(self, tmp_path):
        f = tmp_path / "no_enabled.yaml"
        f.write_text("""
models:
  tesseract:
    language: ja
""")
        config = load_ocr_config(f)
        assert config["tesseract"].enabled is True

    def test_load_ocr_config_extra_fields_in_parameters(self, tmp_path):
        f = tmp_path / "extra.yaml"
        f.write_text("""
models:
  tesseract:
    enabled: true
    languages: ["eng", "jpn"]
    psm: 3
    oem: 3
""")
        config = load_ocr_config(f)
        assert config["tesseract"].parameters["psm"] == 3
        assert config["tesseract"].parameters["oem"] == 3

    def test_load_ocr_config_languages_aliased_to_language(self, tmp_path):
        f = tmp_path / "alias.yaml"
        f.write_text("""
models:
  tesseract:
    enabled: true
    languages: ["eng", "jpn"]
""")
        config = load_ocr_config(f)
        assert config["tesseract"].language == ["eng", "jpn"]
        assert "languages" not in config["tesseract"].parameters

    def test_load_ocr_config_typo_raises_validation_error(self, tmp_path):
        f = tmp_path / "typo.yaml"
        f.write_text("""
models:
  tesseract:
    enabled: true
    langauges: ["eng", "jpn"]
""")
        with pytest.raises(ConfigurationError):
            load_ocr_config(f)

    def test_model_config_typo_raises_validation_error_directly(self):
        with pytest.raises(ValidationError):
            ModelConfig(__key__="tesseract", langauges=["eng", "jpn"])

    def test_model_config_routes_extras_to_parameters(self):
        mc = ModelConfig(__key__="tesseract", psm=3, oem=3, languages=["eng", "jpn"])
        assert mc.name == "tesseract"
        assert mc.language == ["eng", "jpn"]
        assert mc.parameters["psm"] == 3
        assert mc.parameters["oem"] == 3

    def test_model_config_languages_aliased(self):
        mc = ModelConfig(__key__="paddle", languages=["en", "ja"])
        assert mc.name == "paddle"
        assert mc.language == ["en", "ja"]
        assert "languages" not in mc.parameters

    def test_load_ocr_config_unknown_model_name(self, tmp_path, caplog):
        import logging

        f = tmp_path / "unknown.yaml"
        f.write_text("""
models:
  unknown_model:
    enabled: true
""")
        with caplog.at_level(logging.WARNING):
            config = load_ocr_config(f)
        assert "Unknown model" in caplog.text
        assert "unknown_model" in config
