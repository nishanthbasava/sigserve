"""End-to-end test against a running docker-compose stack.

Excluded from the default pytest run; select with `pytest -m integration`
after `docker compose up -d --build`.
"""

import os
import time

import httpx
import pytest

API_URL = os.environ.get("SIGSERVE_API_URL", "http://localhost:8000")

pytestmark = pytest.mark.integration


def wait_for_api(timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{API_URL}/health", timeout=2.0).status_code == 200:
                return
        except httpx.TransportError:
            time.sleep(1.0)
    pytest.fail(f"API at {API_URL} did not become healthy within {timeout}s")


def test_submit_and_poll_end_to_end() -> None:
    wait_for_api()

    payload = {"matrix": [[1, 2], [3, 4]], "params": {"rank": 3}}
    response = httpx.post(f"{API_URL}/jobs", json=payload, timeout=10.0)
    assert response.status_code == 202
    job_id = response.json()["id"]

    body = None
    deadline = time.monotonic() + 60.0
    while time.monotonic() < deadline:
        body = httpx.get(f"{API_URL}/jobs/{job_id}", timeout=10.0).json()
        if body["status"] in ("finished", "failed"):
            break
        time.sleep(1.0)

    assert body is not None
    assert body["status"] == "finished", f"job did not finish: {body}"
    assert len(body["result"]["signatures"]) == 2  # mutation types
    assert len(body["result"]["exposures"]) == 3  # rank
