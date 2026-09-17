from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from sigserve import tasks
from sigserve.db import open_session
from sigserve.models import ApiKey, Job


def test_submit_and_poll(client: TestClient) -> None:
    payload = {"matrix": [[1, 2], [3, 4]], "params": {"rank": 2}}
    response = client.post("/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["id"]

    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "finished"

    result = client.get(f"/jobs/{job_id}/results").json()["result"]
    assert len(result["signatures"]) == 2  # mutation types
    assert len(result["exposures"]) == 2  # rank
    assert "diagnostics" in result


def test_results_unavailable_until_finished(client: TestClient) -> None:
    with open_session() as session:
        key_id = session.scalar(select(ApiKey.id))
        job = Job(params={"rank": 1}, api_key_id=key_id, status="running")
        session.add(job)
        session.commit()
        job_id = job.id

    response = client.get(f"/jobs/{job_id}/results")
    assert response.status_code == 409
    assert "running" in response.json()["detail"]


def test_job_row_records_timestamps(client: TestClient) -> None:
    response = client.post("/jobs", json={"matrix": [[1]], "params": {"rank": 1}})
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
        key_id = session.scalar(select(ApiKey.id))
        job = Job(params={"rank": 2}, api_key_id=key_id)
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
