from collections.abc import Iterator

import fakeredis
import pytest
from fastapi.testclient import TestClient
from rq import Queue
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from sigserve import db
from sigserve.auth import hash_key
from sigserve.main import app
from sigserve.models import ApiKey, Base
from sigserve.queue import get_queue

TEST_API_KEY = "sgs_test_key"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    with db.open_session() as session:
        session.add(ApiKey(name="test", key_hash=hash_key(TEST_API_KEY)))
        session.commit()

    queue = Queue("sigserve-test", connection=fakeredis.FakeRedis(), is_async=False)
    app.dependency_overrides[get_queue] = lambda: queue

    with TestClient(app) as test_client:
        test_client.headers["X-API-Key"] = TEST_API_KEY
        yield test_client
    app.dependency_overrides.clear()
