from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select

from sigserve import tasks
from sigserve.db import open_session
from sigserve.models import ApiKey, Job


def _create_job(status: str = "queued") -> str:
    with open_session() as session:
        key_id = session.scalar(select(ApiKey.id).where(ApiKey.name == "test"))
        job = Job(params={"rank": 1}, api_key_id=key_id, status=status)
        session.add(job)
        session.commit()
        return job.id


def _status(job_id: str) -> str:
    with open_session() as session:
        return session.get(Job, job_id).status


def test_cancel_queued_job(client: TestClient) -> None:
    job_id = _create_job()
    response = client.delete(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "canceled"
    assert client.get(f"/jobs/{job_id}").json()["status"] == "canceled"


def test_cancel_running_job(client: TestClient) -> None:
    job_id = _create_job(status="running")
    response = client.delete(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "canceled"


def test_cancel_finished_job_conflicts(client: TestClient) -> None:
    job_id = _create_job(status="finished")
    assert client.delete(f"/jobs/{job_id}").status_code == 409


def test_cancel_unknown_job(client: TestClient) -> None:
    assert client.delete("/jobs/does-not-exist").status_code == 404


def test_finalize_does_not_overwrite_cancellation(client: TestClient) -> None:
    job_id = _create_job(status="running")
    client.delete(f"/jobs/{job_id}")

    tasks._finalize(job_id, "finished", result={"late": True})
    assert _status(job_id) == "canceled"


def test_failure_callback_marks_job_failed(client: TestClient) -> None:
    job_id = _create_job(status="running")
    fake_rq_job = SimpleNamespace(id=job_id)

    error = RuntimeError("work-horse terminated unexpectedly")
    tasks.mark_job_failed(fake_rq_job, None, RuntimeError, error, None)

    with open_session() as session:
        job = session.get(Job, job_id)
    assert job.status == "failed"
    assert "work-horse terminated unexpectedly" in job.error


def test_failure_callback_respects_terminal_status(client: TestClient) -> None:
    job_id = _create_job(status="running")
    client.delete(f"/jobs/{job_id}")

    fake_rq_job = SimpleNamespace(id=job_id)
    tasks.mark_job_failed(fake_rq_job, None, RuntimeError, RuntimeError("late"), None)
    assert _status(job_id) == "canceled"
