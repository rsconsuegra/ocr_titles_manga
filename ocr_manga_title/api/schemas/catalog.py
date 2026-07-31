"""Pydantic schemas for catalog entry API requests and responses."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from ocr_manga_title.api.schemas._base import ORMSchema


class CatalogEntryResponse(ORMSchema):
    """Serialized catalog entry returned by the API."""

    id: uuid.UUID
    title_en: str | None = None
    title_ja: str | None = None
    code: str | None = None
    source_run_id: uuid.UUID
    confidence: float
    status: str
    created_at: datetime
    updated_at: datetime | None = None


class CatalogUpdateRequest(BaseModel):
    """Payload for partially updating a catalog entry."""

    status: str | None = None
    title_en: str | None = None
    title_ja: str | None = None
    code: str | None = None
