"""Configuration loading for the manga title OCR pipeline.

Reads TOML (app-level) and YAML (per-model OCR) config files, validates them
through Pydantic schemas, and raises :class:`~ocr_manga_title.exceptions.ConfigurationError`
on any structural or semantic problem.
"""

import functools
import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path

import yaml

from ocr_manga_title.engine.registry import MODEL_REGISTRY
from ocr_manga_title.exceptions import ConfigurationError
from ocr_manga_title.schemas import AppConfig, ModelConfig, PreProcessConfig
from ocr_manga_title.settings import (
    CONFIG_PATH,
    OCR_CONFIG_PATH,
    OPENROUTER_API_KEY,
    PREPROCESS_CONFIG_PATH,
)

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def load_config(config_path: str | Path = CONFIG_PATH) -> AppConfig:
    """Load and validate the main application configuration from a TOML file.

    Args:
        config_path: Path to the TOML configuration file.

    Returns:
        Validated :class:`~ocr_manga_title.schemas.AppConfig` instance.

    Raises:
        ConfigurationError: If the file is missing, empty, has invalid TOML syntax,
            or fails Pydantic validation.

    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise ConfigurationError(
            f"Configuration file not found: {config_path}", file_path=str(config_path)
        )

    content = config_path.read_text()
    if not content.strip():
        raise ConfigurationError(
            f"Configuration file is empty: {config_path}", file_path=str(config_path)
        )

    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as e:
        raise ConfigurationError(
            f"Invalid TOML syntax: {e}", file_path=str(config_path)
        ) from e

    if "openrouter" in data and "api_key" not in data.get("openrouter", {}):
        env_key = OPENROUTER_API_KEY
        if env_key:
            data.setdefault("openrouter", {})["api_key"] = env_key

    try:
        return AppConfig(**data)
    except (ValueError, TypeError) as e:
        raise ConfigurationError(str(e), file_path=str(config_path)) from e


@functools.lru_cache(maxsize=1)
def load_ocr_config(
    config_path: str | Path = OCR_CONFIG_PATH,
) -> dict[str, ModelConfig]:
    """Load per-model OCR configuration from a YAML file.

    The YAML file must contain a top-level ``models`` key mapping model names
    to their configuration dicts.  Unknown model names are accepted but logged
    as warnings; all extra keys are collected into each model's ``parameters`` dict.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Mapping of model name to :class:`~ocr_manga_title.schemas.ModelConfig`.

    Raises:
        ConfigurationError: If the file is missing, empty, has invalid YAML syntax,
            or lacks the required ``models`` key.

    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise ConfigurationError(
            f"Configuration file not found: {config_path}", file_path=str(config_path)
        )

    content = config_path.read_text()
    if not content.strip():
        raise ConfigurationError(
            f"Configuration file is empty: {config_path}", file_path=str(config_path)
        )

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Invalid YAML syntax: {e}", file_path=str(config_path)
        ) from e

    if not isinstance(data, dict) or "models" not in data:
        raise ConfigurationError("Missing 'models' key", file_path=str(config_path))

    models: dict[str, ModelConfig] = {}
    for name, model_data in data["models"].items():
        if not isinstance(model_data, dict):
            model_data = {}

        if name not in MODEL_REGISTRY:
            logger.warning("Unknown model '%s' in config", name)

        try:
            models[name] = ModelConfig(**{"__key__": name, **model_data})
        except (ValueError, TypeError) as e:
            raise ConfigurationError(str(e), file_path=str(config_path)) from e

    return models


def load_preprocess_config(config_path: str | Path = PREPROCESS_CONFIG_PATH) -> dict:
    """Load preprocessing configuration from a YAML file.

    Returns a raw dict for flexibility — individual step classes access their own keys.
    If the file is missing or empty, returns a disabled-by-default config so the
    pipeline degrades gracefully without requiring a preprocess.yaml file.

    The config is validated against :class:`~ocr_manga_title.schemas.PreProcessConfig`
    internally, but the raw dict is returned for compatibility with the pipeline.
    """
    disabled = {"preprocessing": {"enabled": False}}

    config_path = Path(config_path)
    if not config_path.exists():
        return disabled

    content = config_path.read_text()
    if not content.strip():
        return disabled

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.warning("Invalid YAML in %s: %s", config_path, e)
        return disabled

    if not isinstance(data, dict) or "preprocessing" not in data:
        return disabled

    try:
        PreProcessConfig(**data["preprocessing"])
    except (ValueError, TypeError) as e:
        logger.warning("Invalid preprocess config: %s", e)
        return disabled

    return data


@dataclass(frozen=True)
class ResolvedModelConfig:
    """Merged model config: YAML defaults + optional DB override."""

    name: str
    enabled: bool
    parameters: dict


def resolve_model_configs(db_overrides: dict[str, dict]) -> dict[str, ResolvedModelConfig]:
    """Merge registry defaults, YAML config, and DB overrides into final configs.

    Resolution order (later wins):
      1. Registry descriptor param defaults
      2. ``config/ocrs.yaml`` values (``enabled`` + param overrides)
      3. DB row values (only for models where a row exists)

    Args:
        db_overrides: Mapping of model name to a dict with optional keys
            ``is_enabled`` and ``parameters``.  Only models present in this
            dict are treated as having a DB override.

    Returns:
        Mapping of model name to :class:`ResolvedModelConfig`.

    """
    try:
        yaml_configs = load_ocr_config()
    except (ConfigurationError, Exception):
        yaml_configs = {}

    resolved: dict[str, ResolvedModelConfig] = {}

    for name, descriptor in MODEL_REGISTRY.items():
        registry_defaults = {p.name: p.default for p in descriptor.params}

        yaml_cfg = yaml_configs.get(name)
        yaml_enabled = yaml_cfg.enabled if yaml_cfg else True
        yaml_params = yaml_cfg.parameters if yaml_cfg else {}

        merged_params = {**registry_defaults, **yaml_params}

        db_row = db_overrides.get(name)
        if db_row is not None:
            enabled = db_row.get("is_enabled", yaml_enabled)
            if db_row.get("parameters"):
                merged_params = {**merged_params, **db_row["parameters"]}
        else:
            enabled = yaml_enabled

        resolved[name] = ResolvedModelConfig(
            name=name,
            enabled=enabled,
            parameters=merged_params,
        )

    return resolved
