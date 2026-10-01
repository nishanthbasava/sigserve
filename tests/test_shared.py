"""Shared (unauthenticated) result pages, self-serve keys, and re-run."""

from fastapi.testclient import TestClient

SUBMISSION = {
    "matrix": [[1, 2], [3, 4], [5, 6]],
    "params": {"rank": 2},
    "name": "shared-me",
}


def _submit(client: TestClient) -> str:
    return client.post("/jobs", json=SUBMISSION).json()["id"]


def test_shared_status_and_results_need_no_key(client: TestClient) -> None:
    job_id = _submit(client)
    del client.headers["X-API-Key"]

    status = client.get(f"/shared/jobs/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "finished"

    results = client.get(f"/shared/jobs/{job_id}/results")
    assert results.status_code == 200
    body = results.json()
    assert body["name"] == "shared-me"
    assert "signatures" in body["result"]


def test_shared_unknown_job_404(client: TestClient) -> None:
    del client.headers["X-API-Key"]
    assert client.get("/shared/jobs/nope").status_code == 404
    assert client.get("/shared/jobs/nope/results").status_code == 404


def test_shared_results_409_until_finished(client: TestClient) -> None:
    # The inline test queue finishes jobs synchronously, so create a
    # still-running row directly.
    from sqlalchemy import select

    from sigserve.db import open_session
    from sigserve.models import ApiKey, Job

    with open_session() as session:
        key_id = session.scalar(select(ApiKey.id))
        job = Job(params={}, api_key_id=key_id, status="running", matrix=[[1]])
        session.add(job)
        session.commit()
        job_id = job.id

    del client.headers["X-API-Key"]
    response = client.get(f"/shared/jobs/{job_id}/results")
    assert response.status_code == 409


def test_self_serve_key_mint_and_use(client: TestClient) -> None:
    del client.headers["X-API-Key"]
    created = client.post("/keys", json={"name": "browser"})
    assert created.status_code == 201
    body = created.json()
    assert body["key"].startswith("sgs_")

    client.headers["X-API-Key"] = body["key"]
    job_id = client.post("/jobs", json=SUBMISSION).json()["id"]
    assert client.get(f"/jobs/{job_id}").status_code == 200
    # The new key sees only its own jobs.
    assert [j["id"] for j in client.get("/jobs").json()] == [job_id]


def test_key_minting_rate_limited(client: TestClient) -> None:
    del client.headers["X-API-Key"]
    codes = [client.post("/keys", json={}).status_code for _ in range(11)]
    assert codes[:10] == [201] * 10
    assert codes[10] == 429


def test_rerun_reuses_input_and_params(client: TestClient) -> None:
    job_id = _submit(client)
    rerun = client.post(f"/jobs/{job_id}/rerun")
    assert rerun.status_code == 202
    new_id = rerun.json()["id"]
    assert new_id != job_id

    body = client.get(f"/jobs/{new_id}").json()
    assert body["status"] == "finished"
    assert body["name"] == "shared-me"
    assert body["params"]["rank"] == 2
    assert body["n_mutation_types"] == 3


def test_rerun_unknown_job_404(client: TestClient) -> None:
    assert client.post("/jobs/nope/rerun").status_code == 404


def test_rerun_without_stored_matrix_409(client: TestClient) -> None:
    from sqlalchemy import select

    from sigserve.db import open_session
    from sigserve.models import ApiKey, Job

    with open_session() as session:
        key_id = session.scalar(select(ApiKey.id))
        job = Job(params={"rank": 1}, api_key_id=key_id, status="finished")
        session.add(job)
        session.commit()
        job_id = job.id

    assert client.post(f"/jobs/{job_id}/rerun").status_code == 409


def test_meta_reports_limits(client: TestClient) -> None:
    del client.headers["X-API-Key"]
    body = client.get("/meta").json()
    assert body["max_mutation_types"] == 2000
    assert body["version"]
