"""Pydantic schemas for post-processing result API requests and responses."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from ocr_manga_title.api.schemas._base import ORMSchema


class PostProcessingResultResponse(ORMSchema):
    """Serialized post-processing result returned by the API."""

    id: uuid.UUID
    title_en: str | None = None
    title_ja: str | None = None
    code: str | None = None
    confidence: float
    processing_type: str
    raw_response: str | None = None
    extra_metadata: dict[str, Any] | None = None
    created_at: datetime


class ResultOverrideRequest(BaseModel):
    """Payload for overriding title fields on a post-processing result."""

    title_en: str | None = None
    title_ja: str | None = None
    code: str | None = None
