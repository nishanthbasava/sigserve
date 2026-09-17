from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from sigserve import maintenance
from sigserve.db import open_session
from sigserve.models import ApiKey, Job


def _create_job(status: str, started_ago: float = 0, finished_ago: float | None = None) -> str:
    now = datetime.now(UTC)
    with open_session() as session:
        key_id = session.scalar(select(ApiKey.id))
        job = Job(
            params={"rank": 1},
            api_key_id=key_id,
            status=status,
            started_at=now - timedelta(seconds=started_ago),
            finished_at=(now - timedelta(seconds=finished_ago)) if finished_ago else None,
        )
        session.add(job)
        session.commit()
        return job.id


def _status(job_id: str) -> str | None:
    with open_session() as session:
        job = session.get(Job, job_id)
        return job.status if job else None


def test_stale_running_job_marked_failed(client: TestClient) -> None:
    stale_id = _create_job("running", started_ago=2 * 3600)  # past timeout + grace
    fresh_id = _create_job("running", started_ago=60)

    assert maintenance.fail_stale_running_jobs() == 1
    assert _status(stale_id) == "failed"
    assert _status(fresh_id) == "running"

    with open_session() as session:
        assert "stale" in session.get(Job, stale_id).error


def test_old_terminal_jobs_deleted(client: TestClient) -> None:
    month = 31 * 24 * 3600
    old_finished = _create_job("finished", finished_ago=month)
    old_canceled = _create_job("canceled", finished_ago=month)
    recent_finished = _create_job("finished", finished_ago=3600)
    old_running = _create_job("running", started_ago=month)

    assert maintenance.delete_old_jobs() == 2
    assert _status(old_finished) is None
    assert _status(old_canceled) is None
    assert _status(recent_finished) == "finished"
    assert _status(old_running) == "running"  # never deleted, only failed by staleness
