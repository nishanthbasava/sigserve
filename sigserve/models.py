import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    api_key_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("api_keys.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued")
    # Optional human-readable dataset name, shown in the jobs table.
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    # Axis labels for plotting: {"mutation_types": [...], "sample_names": [...]}.
    labels: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # The submitted counts matrix. Persisted so results pages are
    # self-contained and failed jobs can be re-run with identical input;
    # previously it lived only in the transient RQ payload.
    matrix: Mapped[list[list[int]] | None] = mapped_column(JSON, nullable=True)
    # Worker-written progress: {"stage": ..., "log_tail": [...], "updated_at": ...}.
    progress: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Matrix dimensions, kept out of params so analytics can filter and
    # bucket on them without unpacking JSON. Nullable: jobs predating the
    # columns have no recorded shape.
    n_mutation_types: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_samples: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
