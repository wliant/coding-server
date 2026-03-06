"""Unit tests for worker.lease_manager — written FIRST per TDD (Constitution II).

Tests run against SQLite in-memory DB via the db_session fixture.
All tests should FAIL until lease_manager.py is implemented.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from worker.models import Job, Project


async def _seed_job(db_session, status: str = "pending") -> Job:
    """Helper: insert a project + job and return the Job."""
    project = Project(
        name="test-project",
        source_type="new",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Build something",
        status=status,
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def test_acquire_lease_sets_in_progress_and_lease_fields(db_session):
    """acquire_lease on a pending job sets status=in_progress, lease_holder, lease_expires_at."""
    from worker.lease_manager import acquire_lease

    job = await _seed_job(db_session, status="pending")
    worker_id = str(uuid.uuid4())
    ttl = 300

    acquired = await acquire_lease(db_session, job.id, worker_id, ttl)

    assert acquired is True
    await db_session.refresh(job)
    assert job.status == "in_progress"
    assert job.lease_holder == worker_id
    assert job.lease_expires_at is not None
    assert job.started_at is not None


async def test_acquire_lease_race_returns_false(db_session):
    """acquire_lease on an already in_progress job (race condition) returns False."""
    from worker.lease_manager import acquire_lease

    job = await _seed_job(db_session, status="in_progress")
    worker_id = str(uuid.uuid4())

    acquired = await acquire_lease(db_session, job.id, worker_id, 300)

    assert acquired is False


async def test_acquire_lease_on_nonexistent_job_returns_false(db_session):
    """acquire_lease on a non-existent job_id returns False."""
    from worker.lease_manager import acquire_lease

    acquired = await acquire_lease(db_session, uuid.uuid4(), str(uuid.uuid4()), 300)

    assert acquired is False


async def test_renew_lease_extends_expiry(db_session):
    """renew_lease extends lease_expires_at for the current holder."""
    from worker.lease_manager import acquire_lease, renew_lease

    job = await _seed_job(db_session, status="pending")
    worker_id = str(uuid.uuid4())
    await acquire_lease(db_session, job.id, worker_id, 300)
    await db_session.refresh(job)
    original_expiry = job.lease_expires_at

    await renew_lease(db_session, job.id, worker_id, 600)
    await db_session.refresh(job)

    assert job.lease_expires_at > original_expiry


async def test_release_lease_clears_lease_fields(db_session):
    """release_lease resets lease_holder and lease_expires_at to NULL."""
    from worker.lease_manager import acquire_lease, release_lease

    job = await _seed_job(db_session, status="pending")
    worker_id = str(uuid.uuid4())
    await acquire_lease(db_session, job.id, worker_id, 300)

    await release_lease(db_session, job.id)
    await db_session.refresh(job)

    assert job.lease_holder is None
    assert job.lease_expires_at is None


async def test_reap_expired_leases_resets_expired_in_progress_to_pending(db_session):
    """reap_expired_leases resets in_progress jobs with expired leases back to pending."""
    from worker.lease_manager import reap_expired_leases

    # Manually create an in_progress job with an already-expired lease
    project = Project(name="p", source_type="new", status="active")
    db_session.add(project)
    await db_session.flush()

    expired_time = datetime.now(timezone.utc) - timedelta(seconds=1)
    job = Job(
        project_id=project.id,
        requirement="old task",
        status="in_progress",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
        lease_holder=str(uuid.uuid4()),
        lease_expires_at=expired_time,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    reaped = await reap_expired_leases(db_session)

    await db_session.refresh(job)
    assert job.status == "pending"
    assert job.lease_holder is None
    assert job.lease_expires_at is None
    assert reaped >= 1


async def test_reap_expired_leases_ignores_active_leases(db_session):
    """reap_expired_leases does NOT reset jobs with non-expired leases."""
    from worker.lease_manager import acquire_lease, reap_expired_leases

    job = await _seed_job(db_session, status="pending")
    worker_id = str(uuid.uuid4())
    await acquire_lease(db_session, job.id, worker_id, 300)

    reaped = await reap_expired_leases(db_session)

    await db_session.refresh(job)
    assert job.status == "in_progress"  # should NOT have been reaped
    assert reaped == 0
