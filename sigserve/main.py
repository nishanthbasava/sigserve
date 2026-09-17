from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from rq import Queue
from sqlalchemy.orm import Session

from sigserve.db import get_session
from sigserve.models import Job
from sigserve.queue import get_queue
from sigserve.schemas import JobStatus, JobSubmission
from sigserve.tasks import run_job

app = FastAPI(title="SigServe", version="0.1.0")

QueueDep = Annotated[Queue, Depends(get_queue)]
SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs", response_model=JobStatus, status_code=202)
def submit_job(submission: JobSubmission, queue: QueueDep, session: SessionDep) -> JobStatus:
    job = Job(params=submission.params.model_dump())
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


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str, session: SessionDep) -> JobStatus:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(id=job.id, status=job.status, result=job.result, error=job.error)
