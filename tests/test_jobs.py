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


def test_job_row_records_matrix_dims(client: TestClient) -> None:
    payload = {"matrix": [[1, 2, 3], [4, 5, 6]], "params": {"rank": 2}}
    job_id = client.post("/jobs", json=payload).json()["id"]

    with open_session() as session:
        job = session.get(Job, job_id)
        assert job is not None
        assert job.n_mutation_types == 2
        assert job.n_samples == 3


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


def test_status_and_list_expose_job_metadata(client: TestClient) -> None:
    payload = {"matrix": [[1, 2, 3], [4, 5, 6]], "params": {"rank": 2}}
    submitted = client.post("/jobs", json=payload).json()
    assert submitted["params"]["rank"] == 2
    assert submitted["created_at"] is not None

    body = client.get(f"/jobs/{submitted['id']}").json()
    assert body["n_mutation_types"] == 2
    assert body["n_samples"] == 3
    assert body["started_at"] is not None
    assert body["finished_at"] is not None
    # Jobs run inline under the test queue, so nothing is ever queued.
    assert body["queue_position"] is None

    (summary,) = client.get("/jobs").json()
    assert summary["id"] == submitted["id"]
    assert summary["params"]["rank"] == 2
    assert summary["n_samples"] == 3
    assert summary["started_at"] is not None


def test_validation_error_omits_matrix_echo(client: TestClient) -> None:
    payload = {"matrix": [[1, 2], [3, -4]], "params": {"rank": 1}}
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("non-negative" in error["msg"] for error in detail)
    assert all("input" not in error for error in detail)


def test_get_unknown_job(client: TestClient) -> None:
    response = client.get("/jobs/does-not-exist")
    assert response.status_code == 404


def test_submit_rejects_bad_rank(client: TestClient) -> None:
    payload = {"matrix": [[1]], "params": {"rank": 0}}
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422
