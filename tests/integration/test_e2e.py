"""End-to-end test against a running docker-compose stack.

Excluded from the default pytest run; select with `pytest -m integration`
after `docker compose up -d --build`.
"""

import os
import subprocess
import time

import httpx
import pytest

API_URL = os.environ.get("SIGSERVE_API_URL", "http://localhost:8000")

pytestmark = pytest.mark.integration


def mint_api_key() -> str:
    output = subprocess.run(
        ["docker", "compose", "exec", "-T", "api"]
        + ["python", "-m", "sigserve.cli", "create-key", "--name", "e2e"],
        check=True,
        capture_output=True,
        text=True,
    )
    return output.stdout.strip().splitlines()[-1]


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
    headers = {"X-API-Key": mint_api_key()}

    # Small but non-degenerate count matrix: 20 mutation types x 8 samples.
    # Iterations are capped low so the real sampler finishes in well under
    # a minute; the goal is exercising the full pipeline, not convergence.
    matrix = [[(i * 7 + j * 3) % 10 + 1 for j in range(8)] for i in range(20)]
    payload = {"matrix": matrix, "params": {"rank": 2, "max_iters": 300}}
    response = httpx.post(f"{API_URL}/jobs", json=payload, headers=headers, timeout=10.0)
    assert response.status_code == 202
    job_id = response.json()["id"]

    body = None
    deadline = time.monotonic() + 300.0
    while time.monotonic() < deadline:
        body = httpx.get(f"{API_URL}/jobs/{job_id}", headers=headers, timeout=10.0).json()
        if body["status"] in ("finished", "failed"):
            break
        time.sleep(2.0)

    assert body is not None
    assert body["status"] == "finished", f"job did not finish: {body}"
    assert len(body["result"]["signatures"]) == 20  # mutation types
    assert all(len(row) == 2 for row in body["result"]["signatures"])  # rank
    assert len(body["result"]["exposures"]) == 2  # rank
    assert all(len(row) == 8 for row in body["result"]["exposures"])  # samples
    assert body["result"]["diagnostics"]["engine"] == "bayesNMF"
