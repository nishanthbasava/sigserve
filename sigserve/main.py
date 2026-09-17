from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from rq import Queue
from sqlalchemy import select
from sqlalchemy.orm import Session

from sigserve.auth import require_api_key
from sigserve.db import get_session
from sigserve.models import ApiKey, Job
from sigserve.queue import get_queue
from sigserve.schemas import JobStatus, JobSubmission, JobSummary
from sigserve.tasks import run_job

app = FastAPI(title="SigServe", version="0.1.0")

QueueDep = Annotated[Queue, Depends(get_queue)]
SessionDep = Annotated[Session, Depends(get_session)]
AuthDep = Annotated[ApiKey, Depends(require_api_key)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs", response_model=JobStatus, status_code=202)
def submit_job(
    submission: JobSubmission, queue: QueueDep, session: SessionDep, api_key: AuthDep
) -> JobStatus:
    job = Job(params=submission.params.model_dump(), api_key_id=api_key.id)
    session.add(job)
    session.commit()

    queue.enqueue(
        run_job,
        job.id,
        submission.matrix,
        submission.params.model_dump(),
        job_id=job.id,
    )
    return JobStatus(id=job.id, status=job.status)


@app.get("/jobs", response_model=list[JobSummary])
def list_jobs(session: SessionDep, api_key: AuthDep) -> list[JobSummary]:
    jobs = session.scalars(
        select(Job).where(Job.api_key_id == api_key.id).order_by(Job.created_at.desc())
    ).all()
    return [
        JobSummary(id=j.id, status=j.status, created_at=j.created_at, finished_at=j.finished_at)
        for j in jobs
    ]


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str, session: SessionDep, api_key: AuthDep) -> JobStatus:
    job = session.get(Job, job_id)
    # A foreign job returns the same 404 as a missing one, so job ids
    # cannot be probed for existence.
    if job is None or job.api_key_id != api_key.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(id=job.id, status=job.status, result=job.result, error=job.error)
