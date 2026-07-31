"""Pydantic schemas for pipeline run API requests and responses."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from ocr_manga_title.api.schemas._base import ORMSchema
from ocr_manga_title.api.schemas.results import PostProcessingResultResponse


class PipelineRunResponse(ORMSchema):
    """Serialized pipeline run returned by the API."""

    id: uuid.UUID
    input_image_path: str
    status: str
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class OCRResultResponse(ORMSchema):
    """Serialized OCR result returned by the API."""

    id: uuid.UUID
    model_name: str
    raw_text: str
    confidence: float
    processing_time_ms: int
    error: str | None = None
    blocks: list[dict[str, Any]] | None = None
    created_at: datetime


class OCRResultDetailResponse(OCRResultResponse):
    """OCR result with nested post-processing results."""

    post_processing_results: list[PostProcessingResultResponse] = []


class PipelineActionResponse(BaseModel):
    """Response for pipeline trigger / cancel actions."""

    message: str
    run_id: str


class PipelineRunDetailResponse(PipelineRunResponse):
    """Pipeline run with nested OCR results and post-processing results."""

    ocr_results: list[OCRResultDetailResponse] = []


class PaginatedResponse[T](BaseModel):
    """Generic paginated response wrapper."""

    items: list[T]
    total: int
    limit: int
    offset: int
