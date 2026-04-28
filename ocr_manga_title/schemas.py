"""Pydantic data models for configuration and pipeline results."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

from ocr_manga_title.exceptions import ConfigurationError
from ocr_manga_title.settings import (
    OLLAMA_BASE_URL,
    OLLAMA_DEFAULT_MODEL,
    OLLAMA_TIMEOUT,
    OPENROUTER_API_KEY_PREFIX,
    OPENROUTER_BASE_URL,
    OPENROUTER_DEFAULT_MODEL,
    OPENROUTER_MAX_RETRIES,
    OPENROUTER_REQUEST_TIMEOUT,
)


class OpenRouterConfig(BaseModel):
    """Connection settings for the OpenRouter LLM API."""

    api_key: SecretStr
    default_model: str = OPENROUTER_DEFAULT_MODEL
    base_url: str = OPENROUTER_BASE_URL
    request_timeout: float = OPENROUTER_REQUEST_TIMEOUT
    max_retries: int = OPENROUTER_MAX_RETRIES

    @model_validator(mode="after")
    def validate_api_key_prefix(self) -> "OpenRouterConfig":
        if "openrouter.ai" in self.base_url and not self.api_key.get_secret_value().startswith(OPENROUTER_API_KEY_PREFIX):
            raise ConfigurationError(
                f"API key must start with '{OPENROUTER_API_KEY_PREFIX}'",
                field_name="api_key",
            )
        return self


class OllamaConfig(BaseModel):
    """Connection settings for a remote Ollama instance."""

    base_url: str = OLLAMA_BASE_URL
    default_model: str = OLLAMA_DEFAULT_MODEL
    default_vision_model: str = "llava"
    timeout: float = OLLAMA_TIMEOUT


class LLMPromptConfig(BaseModel):
    """Configurable prompt template for LLM post-processing."""

    system_prompt: str = ""
    user_prompt_template: str = "{ocr_text}"
    temperature: float = 0.1

    max_ocr_chars: int = 0

    def render_user_prompt(self, ocr_text: str) -> str:
        trimmed = ocr_text[:self.max_ocr_chars] if self.max_ocr_chars > 0 else ocr_text
        return self.user_prompt_template.format_map({"ocr_text": trimmed})


class AppConfig(BaseModel):
    """Top-level application configuration loaded from TOML."""

    openrouter: OpenRouterConfig
    ollama: OllamaConfig = OllamaConfig()
    llm_provider: str = "openrouter"


class ModelConfig(BaseModel):
    """Per-OCR-model configuration.

    The ``name`` field is auto-populated from the YAML dict key (via ``__key__``)
    when the model entry is loaded by :func:`~ocr_manga_title.config.load_ocr_config`.

    Any remaining non-schema keys are routed into ``parameters``.  Typos of
    recognised field names raise a ``ValidationError``.
    """

    name: str = ""
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def _resolve_key_alias(cls, data: dict) -> dict:
        if "__key__" in data:
            if "name" not in data:
                data["name"] = data.pop("__key__")
            else:
                data.pop("__key__")
        return data

    @model_validator(mode="before")
    @classmethod
    def route_extras_to_parameters(cls, data: Any) -> Any:
        """Route unrecognised fields into ``parameters``."""
        if not isinstance(data, dict):
            return data

        schema_fields = set(cls.model_fields.keys())
        recognised = schema_fields | {"__key__"}

        for key in data:
            if key not in recognised and _looks_like_typo(key, recognised):
                raise ValueError(
                    f"Unknown field '{key}'. Did you mean one of: {sorted(recognised)}?"
                )

        data = cls._resolve_key_alias(data)
        extras = {k: v for k, v in data.items() if k not in schema_fields}
        if extras:
            data["parameters"] = {**data.get("parameters", {}), **extras}
            for k in extras:
                data.pop(k)
        return data


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
