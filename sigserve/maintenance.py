"""Periodic maintenance: fail orphaned running jobs and prune old ones.

Runs continuously as the compose `maintenance` service, or one sweep at a
time with:

    python -m sigserve.maintenance --once
"""

import argparse
import logging
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from sigserve.config import get_settings
from sigserve.db import open_session
from sigserve.models import Job
from sigserve.tasks import TERMINAL_STATUSES

logger = logging.getLogger(__name__)


def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; Postgres returns aware ones.
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def fail_stale_running_jobs() -> int:
    """Fail running jobs whose worker died without reporting (e.g. host
    crash); normal failures are handled by the RQ on_failure callback."""
    settings = get_settings()
    deadline = datetime.now(UTC) - timedelta(
        seconds=settings.job_timeout_seconds + settings.stale_job_grace_seconds
    )
    failed = 0
    with open_session() as session:
        for job in session.scalars(select(Job).where(Job.status == "running")):
            started = job.started_at or job.created_at
            if started is not None and _as_utc(started) < deadline:
                job.status = "failed"
                job.error = "Worker stopped reporting; job marked stale"
                job.finished_at = datetime.now(UTC)
                failed += 1
        session.commit()
    return failed


def delete_old_jobs() -> int:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=settings.job_retention_days)
    deleted = 0
    with open_session() as session:
        terminal = select(Job).where(Job.status.in_(TERMINAL_STATUSES))
        for job in session.scalars(terminal):
            ended = job.finished_at or job.created_at
            if ended is not None and _as_utc(ended) < cutoff:
                session.delete(job)
                deleted += 1
        session.commit()
    return deleted


def run_once() -> None:
    stale = fail_stale_running_jobs()
    deleted = delete_old_jobs()
    logger.info("maintenance sweep: %d stale jobs failed, %d old jobs deleted", stale, deleted)


def main() -> None:
    parser = argparse.ArgumentParser(prog="sigserve-maintenance")
    parser.add_argument("--once", action="store_true", help="Run one sweep and exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    interval = get_settings().maintenance_interval_seconds
    while True:
        run_once()
        if args.once:
            return
        time.sleep(interval)


if __name__ == "__main__":
    main()
