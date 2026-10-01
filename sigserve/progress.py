"""Worker-side progress reporting.

Lives in its own module so both the sampler layer and the task layer can
import it without a cycle. Progress is written to the job row, which is
what the API already polls; a lost update is harmless.
"""

from datetime import UTC, datetime
from typing import Any

from sigserve.db import open_session
from sigserve.models import Job


def update_progress(job_id: str | None, stage: str, **detail: Any) -> None:
    if job_id is None:
        return
    with open_session() as session:
        job = session.get(Job, job_id)
        # Only a live run may report progress; a cancel or timeout that
        # landed first wins.
        if job is None or job.status != "running":
            return
        job.progress = {
            "stage": stage,
            **detail,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        session.commit()
