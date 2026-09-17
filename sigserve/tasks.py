import time
from datetime import UTC, datetime
from typing import Any

from sigserve.db import open_session
from sigserve.models import Job


def run_job(job_id: str, matrix: list[list[int]], params: dict[str, Any]) -> dict[str, Any]:
    with open_session() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise ValueError(f"Job {job_id} has no database record")

        job.status = "running"
        job.started_at = datetime.now(UTC)
        session.commit()

        try:
            result = _compute(matrix, params)
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = datetime.now(UTC)
            session.commit()
            raise

        job.status = "finished"
        job.result = result
        job.finished_at = datetime.now(UTC)
        session.commit()
        return result


def _compute(matrix: list[list[int]], params: dict[str, Any]) -> dict[str, Any]:
    """Placeholder computation; replaced by the bayesNMF sampler in a later phase."""
    time.sleep(0.5)
    return {
        "note": "dummy result",
        "n_mutation_types": len(matrix),
        "n_samples": len(matrix[0]) if matrix else 0,
        "rank": params["rank"],
    }
