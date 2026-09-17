from fastapi.testclient import TestClient

from sigserve.auth import hash_key
from sigserve.db import open_session
from sigserve.models import ApiKey

PAYLOAD = {"matrix": [[1, 2]], "params": {"rank": 1}}


def _mint_second_key() -> dict[str, str]:
    plaintext = "sgs_other_key"
    with open_session() as session:
        session.add(ApiKey(name="other", key_hash=hash_key(plaintext)))
        session.commit()
    return {"X-API-Key": plaintext}


def test_cannot_read_foreign_job(client: TestClient) -> None:
    job_id = client.post("/jobs", json=PAYLOAD).json()["id"]
    other = _mint_second_key()

    assert client.get(f"/jobs/{job_id}", headers=other).status_code == 404
    assert client.get(f"/jobs/{job_id}").status_code == 200


def test_listing_scoped_to_caller(client: TestClient) -> None:
    my_ids = {client.post("/jobs", json=PAYLOAD).json()["id"] for _ in range(2)}
    other = _mint_second_key()
    other_id = client.post("/jobs", json=PAYLOAD, headers=other).json()["id"]

    mine = client.get("/jobs").json()
    assert {job["id"] for job in mine} == my_ids

    theirs = client.get("/jobs", headers=other).json()
    assert {job["id"] for job in theirs} == {other_id}
    assert all({"id", "status", "created_at"} <= set(job) for job in theirs)
