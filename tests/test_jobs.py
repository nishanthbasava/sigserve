from typing import Any

import pytest
from fastapi.testclient import TestClient

from sigserve import tasks
from sigserve.db import open_session
from sigserve.models import Job


def test_submit_and_poll(client: TestClient) -> None:
    payload = {"matrix": [[1, 2], [3, 4]], "params": {"rank": 3}}
    response = client.post("/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["id"]

    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "finished"
    assert body["result"]["rank"] == 3
    assert body["result"]["n_samples"] == 2


def test_job_row_records_timestamps(client: TestClient) -> None:
    response = client.post("/jobs", json={"matrix": [[1]], "params": {"rank": 2}})
    job_id = response.json()["id"]

    with open_session() as session:
        job = session.get(Job, job_id)
        assert job is not None
        assert job.started_at is not None
        assert job.finished_at is not None


def test_failed_job_records_error(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(matrix: list[list[int]], params: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("sampler exploded")

    monkeypatch.setattr(tasks, "_compute", boom)

    with open_session() as session:
        job = Job(params={"rank": 2})
        session.add(job)
        session.commit()
        job_id = job.id

    with pytest.raises(RuntimeError):
        tasks.run_job(job_id, [[1]], {"rank": 2})

    body = client.get(f"/jobs/{job_id}").json()
    assert body["status"] == "failed"
    assert "sampler exploded" in body["error"]


def test_get_unknown_job(client: TestClient) -> None:
    response = client.get("/jobs/does-not-exist")
    assert response.status_code == 404


def test_submit_rejects_bad_rank(client: TestClient) -> None:
    payload = {"matrix": [[1]], "params": {"rank": 0}}
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422
