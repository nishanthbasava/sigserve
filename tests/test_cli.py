from fastapi.testclient import TestClient
from sqlalchemy import select

from sigserve.auth import hash_key
from sigserve.cli import create_key
from sigserve.db import open_session
from sigserve.models import ApiKey


def test_create_key_stores_only_hash(client: TestClient) -> None:
    plaintext = create_key("alice")

    assert plaintext.startswith("sgs_")
    with open_session() as session:
        stored = session.scalar(select(ApiKey).where(ApiKey.name == "alice"))
        assert stored is not None
        assert stored.key_hash == hash_key(plaintext)
        assert plaintext not in stored.key_hash


def test_minted_key_authenticates(client: TestClient) -> None:
    plaintext = create_key("bob")
    response = client.get("/jobs", headers={"X-API-Key": plaintext})
    assert response.status_code == 200
