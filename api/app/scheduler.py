"""Fax job scheduler backed by APScheduler with SQLAlchemy job store.

Provides a singleton AsyncIOScheduler that persists scheduled jobs to the
application database so they survive server restarts.  Any jobs whose
run_date passed while the server was down will fire within
``misfire_grace_time`` seconds after restart.
"""

from __future__ import annotations

import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore  # type: ignore

from .config import settings

logger = logging.getLogger(__name__)

# Module-level singleton – created lazily via ``init_scheduler()``.
_scheduler: Optional[AsyncIOScheduler] = None


def init_scheduler() -> AsyncIOScheduler:
    """Create (or return existing) scheduler backed by the app DB."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    jobstores = {
        "default": SQLAlchemyJobStore(url=settings.database_url),
    }
    _scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        # Allow jobs that were missed (e.g. during downtime) to still run
        # if they are less than 1 hour late.
        job_defaults={
            "misfire_grace_time": 3600,
            "coalesce": True,
        },
    )
    return _scheduler


def get_scheduler() -> AsyncIOScheduler:
    """Return the scheduler instance, initialising if needed."""
    if _scheduler is None:
        return init_scheduler()
    return _scheduler


def shutdown_scheduler() -> None:
    """Gracefully shut down the scheduler if running."""
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down")
        except Exception as exc:
            logger.warning("Scheduler shutdown error: %s", exc)
        _scheduler = None



