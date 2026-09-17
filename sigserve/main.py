from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from rq import Queue

from sigserve.queue import get_queue
from sigserve.schemas import JobStatus, JobSubmission
from sigserve.tasks import run_job

app = FastAPI(title="SigServe", version="0.1.0")

QueueDep = Annotated[Queue, Depends(get_queue)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs", response_model=JobStatus, status_code=202)
def submit_job(submission: JobSubmission, queue: QueueDep) -> JobStatus:
    job = queue.enqueue(run_job, submission.matrix, submission.params.model_dump())
    return JobStatus(id=job.id, status=job.get_status())


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str, queue: QueueDep) -> JobStatus:
    job = queue.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(id=job.id, status=job.get_status(), result=job.return_value())
