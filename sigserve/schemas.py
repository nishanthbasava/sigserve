from typing import Any

from pydantic import BaseModel, Field


class SamplerParams(BaseModel):
    rank: int = Field(default=5, ge=1, le=20)


class JobSubmission(BaseModel):
    matrix: list[list[int]] = Field(
        description="Mutation-count matrix; rows are mutation types, columns are samples"
    )
    params: SamplerParams = SamplerParams()


class JobStatus(BaseModel):
    id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
