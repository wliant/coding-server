"""Tests for controller heartbeat timeout detection (US3)."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, call

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from controller.delegator import _reap_unreachable_workers
from controller.registry import WorkerRegistry


@pytest.mark.asyncio
async def test_reap_marks_stale_worker_as_unreachable():
    """Worker with heartbeat older than timeout is marked unreachable."""
    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker1:8001")

    # Force heartbeat to be stale
    registry._workers[worker_id].last_heartbeat_at = (
        datetime.now(timezone.utc) - timedelta(seconds=120)
    )

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _reap_unreachable_workers(registry, db, timeout_seconds=60)

    rec = await registry.get(worker_id)
    assert rec is not None
    assert rec.status == "unreachable"


@pytest.mark.asyncio
async def test_reap_resets_associated_job_to_pending():
    """Job assigned to stale worker is reset to pending."""
    registry = WorkerRegistry()
    task_id = str(uuid.uuid4())
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker1:8001")
    registry._workers[worker_id].last_heartbeat_at = (
        datetime.now(timezone.utc) - timedelta(seconds=120)
    )
    registry._workers[worker_id].status = "in_progress"
    registry._workers[worker_id].current_task_id = task_id

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _reap_unreachable_workers(registry, db, timeout_seconds=60)

    # execute was called to reset job to pending
    db.execute.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_reap_clears_assigned_worker_fields_from_job():
    """The DB update resets assigned_worker_id and assigned_worker_url to None."""
    import re
    registry = WorkerRegistry()
    task_id = str(uuid.uuid4())
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker1:8001")
    registry._workers[worker_id].last_heartbeat_at = (
        datetime.now(timezone.utc) - timedelta(seconds=120)
    )
    registry._workers[worker_id].status = "in_progress"
    registry._workers[worker_id].current_task_id = task_id

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _reap_unreachable_workers(registry, db, timeout_seconds=60)

    # Verify the update statement includes assigned_worker_id and assigned_worker_url
    call_args = db.execute.call_args
    stmt = call_args[0][0]
    compiled = str(stmt.compile())
    assert "assigned_worker_id" in compiled
    assert "assigned_worker_url" in compiled


@pytest.mark.asyncio
async def test_reap_does_not_touch_worker_with_fresh_heartbeat():
    """Worker with recent heartbeat is not marked unreachable."""
    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker1:8001")
    # Heartbeat is fresh (registered just now)

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _reap_unreachable_workers(registry, db, timeout_seconds=60)

    rec = await registry.get(worker_id)
    assert rec.status == "free"  # unchanged
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_reap_skips_already_unreachable_worker():
    """Already unreachable workers are not re-reaped."""
    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker1:8001")
    registry._workers[worker_id].status = "unreachable"
    registry._workers[worker_id].last_heartbeat_at = (
        datetime.now(timezone.utc) - timedelta(seconds=200)
    )

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _reap_unreachable_workers(registry, db, timeout_seconds=60)

    # Already unreachable — get_stale_workers excludes them
    db.execute.assert_not_called()
