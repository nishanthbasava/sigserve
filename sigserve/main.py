import os
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from rq import Callback, Queue
from rq.command import send_stop_job_command
from sqlalchemy import select
from sqlalchemy.orm import Session

from sigserve.auth import mint_key, require_api_key
from sigserve.config import get_settings
from sigserve.db import get_session
from sigserve.models import ApiKey, Job
from sigserve.queue import get_queue
from sigserve.schemas import (
    MAX_MUTATION_TYPES,
    MAX_SAMPLES,
    JobResult,
    JobStatus,
    JobSubmission,
    JobSummary,
    KeyCreated,
    KeyRequest,
)
from sigserve.tasks import TERMINAL_STATUSES, mark_job_failed, run_job

app = FastAPI(title="SigServe", version="0.1.0")

QueueDep = Annotated[Queue, Depends(get_queue)]
SessionDep = Annotated[Session, Depends(get_session)]
AuthDep = Annotated[ApiKey, Depends(require_api_key)]


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # The default handler echoes the invalid input back; for a matrix
    # submission that is the entire matrix, so keep only loc/msg/type.
    detail = [
        {"loc": error.get("loc", []), "msg": error.get("msg", ""), "type": error.get("type", "")}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": detail})


def _queue_position(queue: Queue, job: Job) -> int | None:
    if job.status != "queued":
        return None
    try:
        position = queue.get_job_position(job.id)
    except Exception:
        return None
    return position + 1 if position is not None else None


def _job_status(job: Job, queue: Queue | None = None) -> JobStatus:
    return JobStatus(
        id=job.id,
        status=job.status,
        name=job.name,
        error=job.error,
        progress=job.progress,
        params=job.params,
        n_mutation_types=job.n_mutation_types,
        n_samples=job.n_samples,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        queue_position=_queue_position(queue, job) if queue is not None else None,
    )


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit(queue: Queue, bucket: str, limit: int) -> None:
    """Fixed-window hourly counter in Redis; fails open if Redis is down
    so an outage degrades to no limiting rather than no service."""
    window = datetime.now(UTC).strftime("%Y%m%d%H")
    redis_key = f"sigserve:ratelimit:{bucket}:{window}"
    try:
        count = queue.connection.incr(redis_key)
        if count == 1:
            queue.connection.expire(redis_key, 3600)
    except Exception:
        return
    if count > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded; try again later")


def _job_result(job: Job) -> JobResult:
    return JobResult(
        id=job.id,
        name=job.name,
        params=job.params,
        labels=job.labels,
        created_at=job.created_at,
        finished_at=job.finished_at,
        result=job.result,
    )


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/docs")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/meta")
def meta() -> dict[str, Any]:
    return {
        "version": app.version,
        "max_mutation_types": MAX_MUTATION_TYPES,
        "max_samples": MAX_SAMPLES,
        "bayesnmf_ref": os.environ.get("BAYESNMF_REF"),
    }


@app.post("/keys", response_model=KeyCreated, status_code=201)
def create_api_key(
    body: KeyRequest, request: Request, session: SessionDep, queue: QueueDep
) -> KeyCreated:
    """Self-serve key minting so the web UI works without an operator.

    Keys scope job listings per browser; the per-IP rate limit keeps
    minting from being free DoS ammunition."""
    _rate_limit(queue, f"keys:{_client_ip(request)}", get_settings().key_mint_per_hour)
    api_key, plaintext = mint_key(session, body.name or "web")
    return KeyCreated(id=api_key.id, name=api_key.name, key=plaintext)


@app.post("/jobs", response_model=JobStatus, status_code=202)
def submit_job(
    submission: JobSubmission, queue: QueueDep, session: SessionDep, api_key: AuthDep
) -> JobStatus:
    _rate_limit(queue, f"jobs:{api_key.id}", get_settings().jobs_per_key_per_hour)
    job = Job(
        params=submission.params.model_dump(),
        api_key_id=api_key.id,
        name=submission.name,
        labels=submission.label_dict(),
        matrix=submission.matrix,
        n_mutation_types=len(submission.matrix),
        n_samples=len(submission.matrix[0]),
    )
    session.add(job)
    session.commit()
    _enqueue(queue, job.id)
    return _job_status(job, queue)


def _enqueue(queue: Queue, job_id: str) -> None:
    # The worker loads matrix and params from the job row, so the Redis
    # payload stays small regardless of matrix size.
    queue.enqueue(
        run_job,
        job_id,
        job_id=job_id,
        job_timeout=get_settings().job_timeout_seconds,
        on_failure=Callback(mark_job_failed),
    )


@app.get("/jobs", response_model=list[JobSummary])
def list_jobs(session: SessionDep, api_key: AuthDep) -> list[JobSummary]:
    jobs = session.scalars(
        select(Job).where(Job.api_key_id == api_key.id).order_by(Job.created_at.desc())
    ).all()
    return [
        JobSummary(
            id=j.id,
            status=j.status,
            name=j.name,
            params=j.params,
            n_mutation_types=j.n_mutation_types,
            n_samples=j.n_samples,
            error=j.error,
            created_at=j.created_at,
            started_at=j.started_at,
            finished_at=j.finished_at,
        )
        for j in jobs
    ]


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str, session: SessionDep, queue: QueueDep, api_key: AuthDep) -> JobStatus:
    job = session.get(Job, job_id)
    # A foreign job returns the same 404 as a missing one, so job ids
    # cannot be probed for existence.
    if job is None or job.api_key_id != api_key.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_status(job, queue)


@app.get("/jobs/{job_id}/results", response_model=JobResult)
def get_job_results(job_id: str, session: SessionDep, api_key: AuthDep) -> JobResult:
    job = session.get(Job, job_id)
    if job is None or job.api_key_id != api_key.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "finished":
        raise HTTPException(
            status_code=409,
            detail=f"Job is {job.status}; results are available once finished",
        )
    return _job_result(job)


@app.post("/jobs/{job_id}/rerun", response_model=JobStatus, status_code=202)
def rerun_job(
    job_id: str, session: SessionDep, queue: QueueDep, api_key: AuthDep
) -> JobStatus:
    """Resubmit a job's stored input and params as a new job."""
    source = session.get(Job, job_id)
    if source is None or source.api_key_id != api_key.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if source.matrix is None:
        raise HTTPException(
            status_code=409,
            detail="Job predates input persistence and cannot be re-run; submit it again",
        )
    _rate_limit(queue, f"jobs:{api_key.id}", get_settings().jobs_per_key_per_hour)

    job = Job(
        params=source.params,
        api_key_id=api_key.id,
        name=source.name,
        labels=source.labels,
        matrix=source.matrix,
        n_mutation_types=source.n_mutation_types,
        n_samples=source.n_samples,
    )
    session.add(job)
    session.commit()
    _enqueue(queue, job.id)
    return _job_status(job, queue)


# Shared, unauthenticated reads. A job id is a 122-bit random UUID known
# only to its submitter, so the URL itself is the capability (same model
# as a private doc link); the authenticated routes still 404 for foreign
# jobs, and listing always requires a key.


@app.get("/shared/jobs/{job_id}", response_model=JobStatus)
def get_shared_job(job_id: str, session: SessionDep, queue: QueueDep) -> JobStatus:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_status(job, queue)


@app.get("/shared/jobs/{job_id}/results", response_model=JobResult)
def get_shared_job_results(job_id: str, session: SessionDep) -> JobResult:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "finished":
        raise HTTPException(
            status_code=409,
            detail=f"Job is {job.status}; results are available once finished",
        )
    return _job_result(job)


@app.delete("/jobs/{job_id}", response_model=JobStatus)
def cancel_job(
    job_id: str, session: SessionDep, queue: QueueDep, api_key: AuthDep
) -> JobStatus:
    job = session.get(Job, job_id)
    if job is None or job.api_key_id != api_key.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail=f"Job already {job.status}")

    was_running = job.status == "running"
    job.status = "canceled"
    job.error = "Canceled by user"
    job.finished_at = datetime.now(UTC)
    session.commit()

    rq_job = queue.fetch_job(job_id)
    if rq_job is not None:
        if was_running:
            try:
                send_stop_job_command(queue.connection, job_id)
            except Exception:
                # The work-horse may have just exited; the row is already
                # terminal, so the outcome is settled either way.
                pass
        else:
            rq_job.cancel()
    return _job_status(job)
