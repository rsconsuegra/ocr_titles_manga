from datetime import datetime

from pydantic import BaseModel


class ModelConfigResponse(BaseModel):
    """Serialized OCR model configuration returned by the API."""

    model_name: str
    is_enabled: bool
    parameters: dict | None = None
    language_hint: str | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelConfigUpdateRequest(BaseModel):
    """Payload for partially updating an OCR model configuration."""

    is_enabled: bool | None = None
    parameters: dict | None = None
    language_hint: str | None = None
