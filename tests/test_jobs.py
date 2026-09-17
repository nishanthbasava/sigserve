from collections.abc import Iterator

import fakeredis
import pytest
from fastapi.testclient import TestClient
from rq import Queue

from sigserve.main import app
from sigserve.queue import get_queue


@pytest.fixture
def client() -> Iterator[TestClient]:
    connection = fakeredis.FakeRedis()
    queue = Queue("sigserve-test", connection=connection, is_async=False)
    app.dependency_overrides[get_queue] = lambda: queue
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


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


def test_get_unknown_job(client: TestClient) -> None:
    response = client.get("/jobs/does-not-exist")
    assert response.status_code == 404


def test_submit_rejects_bad_rank(client: TestClient) -> None:
    payload = {"matrix": [[1]], "params": {"rank": 0}}
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422
