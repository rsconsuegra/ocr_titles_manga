from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ModelConfigResponse(BaseModel):
    """Serialized OCR model configuration returned by the API."""

    model_name: str
    is_enabled: bool
    parameters: dict[str, Any] | None = None
    language_hint: str | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ModelConfigUpdateRequest(BaseModel):
    """Payload for partially updating an OCR model configuration."""

    is_enabled: bool | None = None
    parameters: dict[str, Any] | None = None
    language_hint: str | None = None
