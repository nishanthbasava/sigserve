from datetime import UTC, datetime
from typing import Any

from sigserve import sampler
from sigserve.db import open_session
from sigserve.models import Job

TERMINAL_STATUSES = ("finished", "failed", "canceled")


def run_job(job_id: str, matrix: list[list[int]], params: dict[str, Any]) -> dict[str, Any]:
    with open_session() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise ValueError(f"Job {job_id} has no database record")
        job.status = "running"
        job.started_at = datetime.now(UTC)
        session.commit()

    # No session is held open during the sampler run; it can take minutes
    # and would otherwise pin a database connection the whole time.
    try:
        result = _compute(matrix, params)
    except Exception as exc:
        _finalize(job_id, "failed", error=str(exc))
        raise

    _finalize(job_id, "finished", result=result)
    return result


def mark_job_failed(
    rq_job: Any, connection: Any, exc_type: type, exc_value: BaseException, traceback: Any
) -> None:
    """RQ on_failure callback: runs in the worker parent, so it also covers
    jobs whose work-horse was killed (timeout, OOM) and never reached
    run_job's own exception handling."""
    _finalize(rq_job.id, "failed", error=f"{exc_type.__name__}: {exc_value}")


def _finalize(
    job_id: str,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    with open_session() as session:
        job = session.get(Job, job_id)
        if job is None or job.status in TERMINAL_STATUSES:
            return
        job.status = status
        job.result = result
        job.error = error
        job.finished_at = datetime.now(UTC)
        session.commit()


def _compute(matrix: list[list[int]], params: dict[str, Any]) -> dict[str, Any]:
    return sampler.run_bayesnmf(matrix, params).to_dict()
