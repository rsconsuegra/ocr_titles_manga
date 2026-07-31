"""Pydantic schemas for OCR model configuration API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from ocr_manga_title.api.schemas._base import ORMSchema


class ModelConfigResponse(ORMSchema):
    """Serialized OCR model configuration returned by the API."""

    model_name: str
    is_enabled: bool
    parameters: dict[str, Any] | None = None
    language_hint: str | None = None
    updated_at: datetime | None = None


class ModelConfigUpdateRequest(BaseModel):
    """Payload for partially updating an OCR model configuration."""

    is_enabled: bool | None = None
    parameters: dict[str, Any] | None = None
    language_hint: str | None = None
