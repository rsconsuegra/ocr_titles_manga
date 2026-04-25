"""Pydantic schemas for the pipeline profiles API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProfileCreateRequest(BaseModel):
    name: str
    description: str | None = None
    preprocess_steps: dict[str, dict[str, Any]] | None = None
    ocr_models: dict[str, dict[str, Any]] | None = None
    enable_llm: bool = False
    is_default: bool = False


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    preprocess_steps: dict[str, dict[str, Any]] | None = None
    ocr_models: dict[str, dict[str, Any]] | None = None
    enable_llm: bool | None = None
    is_default: bool | None = None


class ProfileResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    description: str | None
    preprocess_steps: dict | None
    ocr_models: dict | None
    enable_llm: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime | None
