"""Pydantic schemas for the preprocessing playground API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ParamDescriptorResponse(BaseModel):
    """Schema for a single parameter exposed by a preprocessing step."""

    name: str
    type: str
    default: Any
    label: str = ""
    description: str = ""
    options: list[str] | None = None
    disabled_options: dict[str, str] | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None


class StepDescriptorResponse(BaseModel):
    """Schema for a preprocessing step descriptor."""

    name: str
    label: str
    description: str
    params: list[ParamDescriptorResponse]


class PreviewStepRequest(BaseModel):
    """Request body for single-step preview.

    Deprecated: kept for backward compat. New code uses multipart form fields.
    """

    image: str
    step_name: str
    params: dict[str, Any] = {}


class PreviewStepResponse(BaseModel):
    """Response for single-step preview."""

    image: str
    step_name: str
    metadata: dict[str, Any] = {}
    processing_time_ms: int = 0
    success: bool = True
    error: str | None = None


class PreviewPipelineRequest(BaseModel):
    """Request body for full pipeline preview.

    Deprecated: kept for backward compat. New code uses multipart form fields.
    """

    image: str
    steps: dict[str, dict[str, Any]] = {}


class PipelineStepResult(BaseModel):
    """Result for one step in a pipeline preview."""

    step_name: str
    enabled: bool
    success: bool
    image: str | None = None
    metadata: dict[str, Any] = {}
    processing_time_ms: int = 0
    error: str | None = None


class PreviewPipelineResponse(BaseModel):
    """Response for full pipeline preview with all intermediate images."""

    steps: list[PipelineStepResult]
    total_processing_time_ms: int = 0


class ExportPipelineRequest(BaseModel):
    """Request body for exporting a pipeline config as YAML."""

    steps: dict[str, dict[str, Any]] = {}
