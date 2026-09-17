from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

MAX_MUTATION_TYPES = 2000
MAX_SAMPLES = 2000


class SamplerParams(BaseModel):
    rank: int = Field(default=5, ge=1, le=20)
    max_iters: int = Field(default=2000, ge=100, le=20000)


class JobSubmission(BaseModel):
    matrix: list[list[int]] = Field(
        description="Mutation-count matrix; rows are mutation types, columns are samples"
    )
    params: SamplerParams = SamplerParams()

    @model_validator(mode="after")
    def validate_matrix(self) -> "JobSubmission":
        if not self.matrix or not self.matrix[0]:
            raise ValueError("matrix must have at least one row and one column")

        width = len(self.matrix[0])
        if any(len(row) != width for row in self.matrix):
            raise ValueError("matrix rows must all have the same length")

        if len(self.matrix) > MAX_MUTATION_TYPES:
            raise ValueError(f"matrix exceeds {MAX_MUTATION_TYPES} mutation types")
        if width > MAX_SAMPLES:
            raise ValueError(f"matrix exceeds {MAX_SAMPLES} samples")

        if any(value < 0 for row in self.matrix for value in row):
            raise ValueError("matrix entries must be non-negative counts")

        max_rank = min(len(self.matrix), width)
        if self.params.rank > max_rank:
            raise ValueError(
                f"rank must not exceed the smaller matrix dimension ({max_rank})"
            )
        return self


class JobSummary(BaseModel):
    id: str
    status: str
    created_at: datetime
    finished_at: datetime | None = None


class JobStatus(BaseModel):
    id: str
    status: str
    error: str | None = None


class JobResult(BaseModel):
    id: str
    result: dict[str, Any]
