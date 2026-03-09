"""Tests for controller lease renewal (US3)."""
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from controller.delegator import _renew_active_leases
from controller.registry import WorkerRegistry


@pytest.mark.asyncio
async def test_renew_extends_lease_for_in_progress_worker():
    """in_progress worker with active task gets its lease extended."""
    registry = WorkerRegistry()
    task_id = str(uuid.uuid4())
    worker_id = await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    await registry.assign_task(worker_id, task_id)

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _renew_active_leases(registry, db, lease_ttl_seconds=300)

    db.execute.assert_called_once()
    db.commit.assert_called_once()

    # Verify lease_expires_at is in the update statement
    call_args = db.execute.call_args
    stmt = call_args[0][0]
    compiled = str(stmt.compile())
    assert "lease_expires_at" in compiled


@pytest.mark.asyncio
async def test_renew_skips_free_worker():
    """Free worker has no active task, no DB update needed."""
    registry = WorkerRegistry()
    await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    # Worker stays free, no assign_task

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _renew_active_leases(registry, db, lease_ttl_seconds=300)

    db.execute.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_renew_skips_unreachable_worker():
    """Unreachable worker does not get a lease renewal."""
    registry = WorkerRegistry()
    task_id = str(uuid.uuid4())
    worker_id = await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    await registry.assign_task(worker_id, task_id)
    # Simulate being marked unreachable
    registry._workers[worker_id].status = "unreachable"

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _renew_active_leases(registry, db, lease_ttl_seconds=300)

    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_renew_multiple_in_progress_workers():
    """All in_progress workers get their leases renewed."""
    registry = WorkerRegistry()
    task_id_1 = str(uuid.uuid4())
    task_id_2 = str(uuid.uuid4())
    worker_id_1 = await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    worker_id_2 = await registry.register("worker-2", "simple_crewai_pair_agent", "http://worker2:8001")
    await registry.assign_task(worker_id_1, task_id_1)
    await registry.assign_task(worker_id_2, task_id_2)

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _renew_active_leases(registry, db, lease_ttl_seconds=300)

    assert db.execute.call_count == 2
    db.commit.assert_called_once()
