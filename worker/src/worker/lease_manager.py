"""DB-based lease management for the worker.

Uses atomic SQLAlchemy UPDATE ... WHERE to claim and release task leases.
PostgreSQL MVCC guarantees only one worker wins a concurrent claim on the same row.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from worker.models import Job

logger = logging.getLogger(__name__)


async def acquire_lease(
    db: AsyncSession,
    job_id: uuid.UUID,
    worker_id: str,
    ttl_seconds: int,
) -> bool:
    """Atomically claim a Pending job for this worker.

    Returns True on success, False if the job is no longer Pending (race condition)
    or does not exist.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)

    result = await db.execute(
        update(Job)
        .where(and_(Job.id == job_id, Job.status == "pending"))
        .values(
            status="in_progress",
            lease_holder=worker_id,
            lease_expires_at=expires_at,
            started_at=now,
            updated_at=now,
        )
        .returning(Job.id)
    )
    row = result.fetchone()
    await db.commit()

    if row is None:
        return False

    logger.info(
        "task_claimed",
        extra={"event": "task_claimed", "job_id": str(job_id), "worker_id": worker_id},
    )
    return True


async def renew_lease(
    db: AsyncSession,
    job_id: uuid.UUID,
    worker_id: str,
    ttl_seconds: int,
) -> None:
    """Extend the lease expiry for an active task.

    No-op if the worker no longer holds the lease.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)

    await db.execute(
        update(Job)
        .where(
            and_(
                Job.id == job_id,
                Job.lease_holder == worker_id,
                Job.status == "in_progress",
            )
        )
        .values(lease_expires_at=expires_at, updated_at=now)
    )
    await db.commit()

    logger.info(
        "lease_renewed",
        extra={"event": "lease_renewed", "job_id": str(job_id), "worker_id": worker_id},
    )


async def release_lease(
    db: AsyncSession,
    job_id: uuid.UUID,
) -> None:
    """Clear lease fields (lease_holder, lease_expires_at) for a job.

    Called after the job reaches a terminal state (Completed or Failed).
    """
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(lease_holder=None, lease_expires_at=None, updated_at=now)
    )
    await db.commit()


async def reap_expired_leases(db: AsyncSession) -> int:
    """Reset In Progress jobs with expired leases back to Pending.

    Returns the count of jobs reaped.
    """
    now = datetime.now(timezone.utc)

    result = await db.execute(
        update(Job)
        .where(
            and_(
                Job.status == "in_progress",
                Job.lease_expires_at < now,
            )
        )
        .values(
            status="pending",
            lease_holder=None,
            lease_expires_at=None,
            updated_at=now,
        )
        .returning(Job.id)
    )
    reaped_ids = result.fetchall()
    await db.commit()

    count = len(reaped_ids)
    if count > 0:
        logger.info(
            "lease_reaped",
            extra={"event": "lease_reaped", "count": count},
        )
    return count


async def get_next_pending_job(db: AsyncSession) -> Job | None:
    """Fetch the oldest Pending job, if any."""
    result = await db.execute(
        select(Job)
        .where(Job.status == "pending")
        .order_by(Job.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()
