"""Pydantic schemas for batch run API responses."""

import uuid
from datetime import datetime

from ocr_manga_title.api.schemas._base import ORMSchema
from ocr_manga_title.api.schemas.pipeline import PipelineRunResponse


class BatchRunResponse(ORMSchema):
    """Summary schema for a batch run."""

    id: uuid.UUID
    name: str | None = None
    status: str
    total_count: int
    completed_count: int = 0
    failed_count: int = 0
    created_at: datetime
    completed_at: datetime | None = None


class BatchRunDetailResponse(BatchRunResponse):
    """Detailed batch run response including individual pipeline runs."""

    runs: list[PipelineRunResponse] = []
