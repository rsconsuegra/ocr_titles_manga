import uuid
from datetime import datetime

from pydantic import BaseModel

from ocr_manga_title.api.schemas.pipeline import PipelineRunResponse


class BatchRunResponse(BaseModel):
    id: uuid.UUID
    name: str | None = None
    status: str
    total_count: int
    completed_count: int = 0
    failed_count: int = 0
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class BatchRunDetailResponse(BatchRunResponse):
    runs: list[PipelineRunResponse] = []
