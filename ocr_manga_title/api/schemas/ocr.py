"""Pydantic schemas for the OCR playground and quick-run API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ModelParamDescriptorResponse(BaseModel):
    """Schema for a single parameter exposed by an OCR model."""

    name: str
    type: str
    default: Any
    label: str = ""
    description: str = ""
    options: list[str] | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None


class ModelDescriptorResponse(BaseModel):
    """Schema for an OCR model descriptor."""

    name: str
    label: str
    description: str
    params: list[ModelParamDescriptorResponse]
    available: bool = False
    enabled: bool = False


class OCRRunRequest(BaseModel):
    """Request body for running a single OCR model.

    Deprecated: kept for backward compat. New code uses multipart form fields.
    """

    image: str
    model_name: str
    params: dict[str, Any] = {}
    enable_llm: bool = False


class TextBlockData(BaseModel):
    """A single detected text region with bounding box."""

    bbox: list[list[float]]
    text: str
    confidence: float


class OCRResultData(BaseModel):
    """OCR output from a single model."""

    raw_text: str = ""
    model_name: str
    confidence: float = 0.0
    processing_time_ms: int = 0
    error: str | None = None
    blocks: list[TextBlockData] | None = None


class LLMResultData(BaseModel):
    """LLM post-processing result."""

    title_en: str | None = None
    title_ja: str | None = None
    code: str | None = None
    confidence: float = 0.0
    source_method: str = "llm"
    raw_response: str | None = None
    extra_metadata: dict[str, Any] | None = None


class OCRRunResponse(BaseModel):
    """Response for a single OCR model run."""

    ocr: OCRResultData
    llm: LLMResultData | None = None


class OCRExportRequest(BaseModel):
    """Request body for exporting OCR config as YAML."""

    models: dict[str, dict[str, Any]] = {}


class QuickRunRequest(BaseModel):
    """Request body for the stateless quick-run pipeline.

    Deprecated: kept for backward compat. New code uses multipart form fields.
    """

    image: str
    preprocess_steps: dict[str, dict[str, Any]] = {}
    ocr_models: dict[str, dict[str, Any]] = {}
    enable_llm: bool = False
    profile_id: str | None = None


class QuickRunResponse(BaseModel):
    """Response for the stateless quick-run pipeline."""

    ocr_results: list[OCRResultData] = []
    llm: LLMResultData | None = None
    total_processing_time_ms: int = 0


class YamlExportResponse(BaseModel):
    """Response for YAML config export endpoints."""

    yaml: str
