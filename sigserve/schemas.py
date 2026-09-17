from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SamplerParams(BaseModel):
    rank: int = Field(default=5, ge=1, le=20)
    max_iters: int = Field(default=2000, ge=100, le=20000)


class JobSubmission(BaseModel):
    matrix: list[list[int]] = Field(
        description="Mutation-count matrix; rows are mutation types, columns are samples"
    )
    params: SamplerParams = SamplerParams()


class JobSummary(BaseModel):
    id: str
    status: str
    created_at: datetime
    finished_at: datetime | None = None


class JobStatus(BaseModel):
    id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
