from fastapi.testclient import TestClient
from sqlalchemy import select

from sigserve.db import open_session
from sigserve.models import ApiKey, Job
from sigserve.progress import update_progress


def test_progress_visible_on_running_job(client: TestClient) -> None:
    with open_session() as session:
        key_id = session.scalar(select(ApiKey.id))
        job = Job(params={}, api_key_id=key_id, status="running", matrix=[[1]])
        session.add(job)
        session.commit()
        job_id = job.id

    update_progress(job_id, "sampling", log_tail=["iter = 100"])

    progress = client.get(f"/jobs/{job_id}").json()["progress"]
    assert progress["stage"] == "sampling"
    assert progress["log_tail"] == ["iter = 100"]
    assert progress["updated_at"] is not None


def test_progress_ignored_once_terminal(client: TestClient) -> None:
    with open_session() as session:
        key_id = session.scalar(select(ApiKey.id))
        job = Job(params={}, api_key_id=key_id, status="finished", matrix=[[1]])
        session.add(job)
        session.commit()
        job_id = job.id

    update_progress(job_id, "sampling", log_tail=["late write"])
    update_progress(None, "sampling")  # library use without a job: no-op

    assert client.get(f"/jobs/{job_id}").json()["progress"] is None


def test_submitted_job_clears_progress_when_finished(client: TestClient) -> None:
    # The inline test queue runs the stub synchronously: it writes
    # progress mid-run, then _finalize must clear it.
    job_id = client.post("/jobs", json={"matrix": [[1, 2], [3, 4]], "params": {"rank": 1}}).json()[
        "id"
    ]
    body = client.get(f"/jobs/{job_id}").json()
    assert body["status"] == "finished"
    assert body["progress"] is None
