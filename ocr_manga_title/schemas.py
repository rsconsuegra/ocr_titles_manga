"""Pydantic data models for configuration and pipeline results."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

from ocr_manga_title.exceptions import ConfigurationError
from ocr_manga_title.settings import (
    OPENROUTER_API_KEY_PREFIX,
    OPENROUTER_BASE_URL,
    OPENROUTER_DEFAULT_MODEL,
    OPENROUTER_MAX_RETRIES,
    OPENROUTER_REQUEST_TIMEOUT,
)

_MODEL_ALIASES: dict[str, str] = {"languages": "language"}


class OpenRouterConfig(BaseModel):
    """Connection settings for the OpenRouter LLM API."""

    api_key: SecretStr
    default_model: str = OPENROUTER_DEFAULT_MODEL
    base_url: str = OPENROUTER_BASE_URL
    request_timeout: float = OPENROUTER_REQUEST_TIMEOUT
    max_retries: int = OPENROUTER_MAX_RETRIES

    @field_validator("api_key", mode="before")
    @classmethod
    def validate_api_key(cls, v: str | SecretStr) -> str | SecretStr:
        """Ensure the API key starts with the expected prefix."""
        raw = v.get_secret_value() if isinstance(v, SecretStr) else v
        if not raw.startswith(OPENROUTER_API_KEY_PREFIX):
            raise ConfigurationError(
                f"API key must start with '{OPENROUTER_API_KEY_PREFIX}'",
                field_name="api_key",
            )
        return v


class AppConfig(BaseModel):
    """Top-level application configuration loaded from TOML."""

    images_path: Path
    openrouter: OpenRouterConfig

    @field_validator("images_path")
    @classmethod
    def validate_images_path(cls, v: Path) -> Path:
        """Warn if the configured images directory does not exist."""
        import logging

        if not v.exists():
            logging.warning("images_path does not exist: %s", v)
        return v


class ModelConfig(BaseModel):
    """Per-OCR-model configuration.

    The ``name`` field is auto-populated from the YAML dict key (via ``__key__``)
    when the model entry is loaded by :func:`~ocr_manga_title.config.load_ocr_config`.

    Known aliases (``languages`` → ``language``) are handled by the validator.
    Any remaining non-schema keys are routed into ``parameters``.  Typos of
    recognised field names raise a ``ValidationError``.
    """

    name: str = ""
    enabled: bool = True
    language: str | list[str] = "en"
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def route_extras_to_parameters(cls, data: Any) -> Any:
        """Route unrecognised fields into ``parameters`` and resolve aliases."""
        if not isinstance(data, dict):
            return data

        schema_fields = set(cls.model_fields.keys())
        recognised = schema_fields | set(_MODEL_ALIASES.keys()) | {"__key__"}

        for key in data:
            if key not in recognised and _looks_like_typo(key, recognised):
                raise ValueError(
                    f"Unknown field '{key}'. Did you mean one of: {sorted(recognised)}?"
                )

        routed = dict(data)

        if "__key__" in routed:
            if "name" not in routed:
                routed["name"] = routed.pop("__key__")
            else:
                routed.pop("__key__")

        for alias, target in _MODEL_ALIASES.items():
            if alias in routed and target not in routed:
                routed[target] = routed.pop(alias)
            elif alias in routed:
                routed.pop(alias)

        extras = {k: v for k, v in routed.items() if k not in schema_fields}
        if extras:
            routed["parameters"] = {**routed.get("parameters", {}), **extras}
            for k in extras:
                routed.pop(k)

        return routed


class PreProcessStepConfig(BaseModel):
    """Configuration for a single preprocessing step."""

    enabled: bool = True
    method: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def route_extras(cls, data: Any) -> Any:
        """Route unrecognised fields into ``parameters``."""
        if not isinstance(data, dict):
            return data
        schema_fields = set(cls.model_fields.keys())
        extras = {k: v for k, v in data.items() if k not in schema_fields}
        routed = {k: v for k, v in data.items() if k in schema_fields}
        if extras:
            routed["parameters"] = {**data.get("parameters", {}), **extras}
        return routed


class PreProcessConfig(BaseModel):
    """Top-level preprocessing configuration."""

    enabled: bool = False
    debug: bool = False
    steps: dict[str, PreProcessStepConfig] = Field(default_factory=dict)


def _looks_like_typo(key: str, recognised: set[str]) -> bool:
    for field in recognised:
        if abs(len(key) - len(field)) > 2:
            continue
        if _levenshtein(key, field) <= 2:
            return True
    return False


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        return _levenshtein(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


class OCRResult(BaseModel):
    """Raw output from a single OCR model run."""

    raw_text: str = ""
    model_name: str
    confidence: float = 0.0
    processing_time_ms: int = 0
    error: str | None = None


class ExtractedTitle(BaseModel):
    """Structured title metadata extracted from OCR text by LLM or rules."""

    title_en: str | None = None
    title_ja: str | None = None
    code: str | None = None
    confidence: float = 0.0
    source_model: str | None = None
    source_method: str = "unknown"

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        """Clamp the confidence value to the [0.0, 1.0] range."""
        return max(0.0, min(1.0, v))


class PreProcessStepResult(BaseModel):
    """Outcome of a single preprocessing step execution."""

    step_name: str
    enabled: bool
    success: bool
    processing_time_ms: int = 0
    output_path: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreProcessResult(BaseModel):
    """Aggregate result of the full preprocessing pipeline for one image."""

    input_path: str
    output_path: str | None = None
    steps: list[PreProcessStepResult] = Field(default_factory=list)
    total_processing_time_ms: int = 0


class PipelineResult(BaseModel):
    """Complete output of processing one image through the full pipeline."""

    input_path: str
    ocr_results: list[OCRResult] = Field(default_factory=list)
    extracted: ExtractedTitle | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    errors: list[str] = Field(default_factory=list)
    preprocess_result: PreProcessResult | None = None
