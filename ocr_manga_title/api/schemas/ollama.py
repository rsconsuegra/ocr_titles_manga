"""Pydantic schemas for the Ollama integration API."""

from pydantic import BaseModel


class OllamaStatusResponse(BaseModel):
    """Response for Ollama connection status."""

    configured: bool
    base_url: str
    default_model: str
    default_vision_model: str


class OllamaVisionModelResponse(BaseModel):
    """Response for a single Ollama vision model."""

    name: str
    size: int = 0


class OllamaLLMModelResponse(BaseModel):
    """Response for a single Ollama LLM model."""

    name: str
    size: int = 0
    modified_at: str = ""
    parameter_size: str = ""
    quantization: str = ""


class LLMProviderInfo(BaseModel):
    """Information about a single LLM provider."""

    name: str
    label: str
    available: bool
    configured: bool | None = None
    model_count: int | None = None


class LLMProvidersResponse(BaseModel):
    """Response listing available LLM providers."""

    providers: list[LLMProviderInfo]
