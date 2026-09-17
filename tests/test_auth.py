from fastapi.testclient import TestClient

from sigserve.main import app

PAYLOAD = {"matrix": [[1]], "params": {"rank": 1}}


def test_missing_key_rejected(client: TestClient) -> None:
    bare = TestClient(app)  # no default X-API-Key header; overrides still active
    response = bare.post("/jobs", json=PAYLOAD)
    assert response.status_code == 401


def test_invalid_key_rejected(client: TestClient) -> None:
    response = client.post("/jobs", json=PAYLOAD, headers={"X-API-Key": "sgs_wrong"})
    assert response.status_code == 401


def test_get_requires_key(client: TestClient) -> None:
    bare = TestClient(app)
    response = bare.get("/jobs/some-id")
    assert response.status_code == 401


def test_health_is_public(client: TestClient) -> None:
    bare = TestClient(app)
    assert bare.get("/health").status_code == 200


def test_valid_key_accepted(client: TestClient) -> None:
    response = client.post("/jobs", json=PAYLOAD)
    assert response.status_code == 202
