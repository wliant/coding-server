"""Unit tests for WorkerRegistry (TDD — written before implementation)."""
import asyncio

import pytest

from controller.registry import WorkerRegistry


@pytest.mark.asyncio
async def test_register_returns_worker_id():
    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker:8001")
    assert isinstance(worker_id, str)
    assert len(worker_id) > 0


@pytest.mark.asyncio
async def test_register_status_is_free():
    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker:8001")
    rec = await registry.get(worker_id)
    assert rec is not None
    assert rec.status == "free"


@pytest.mark.asyncio
async def test_register_duplicate_url_replaces_existing():
    registry = WorkerRegistry()
    id1 = await registry.register("simple_crewai_pair_agent", "http://worker:8001")
    id2 = await registry.register("simple_crewai_pair_agent", "http://worker:8001")
    assert id1 != id2
    # Only one record should exist for that URL
    all_workers = await registry.get_all()
    assert len(all_workers) == 1
    assert all_workers[0].worker_id == id2


@pytest.mark.asyncio
async def test_get_free_worker_for_agent_type_returns_free_worker():
    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker:8001")
    result = await registry.get_free_worker_for_agent_type("simple_crewai_pair_agent")
    assert result is not None
    assert result.worker_id == worker_id


@pytest.mark.asyncio
async def test_get_free_worker_returns_none_when_none_free():
    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker:8001")
    await registry.assign_task(worker_id, "task-123")
    result = await registry.get_free_worker_for_agent_type("simple_crewai_pair_agent")
    assert result is None


@pytest.mark.asyncio
async def test_get_free_worker_returns_none_for_unknown_agent_type():
    registry = WorkerRegistry()
    await registry.register("simple_crewai_pair_agent", "http://worker:8001")
    result = await registry.get_free_worker_for_agent_type("other_agent")
    assert result is None


@pytest.mark.asyncio
async def test_mark_unreachable_sets_status():
    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker:8001")
    await registry.mark_unreachable(worker_id)
    rec = await registry.get(worker_id)
    assert rec.status == "unreachable"


@pytest.mark.asyncio
async def test_heartbeat_updates_timestamp_and_status():
    import time
    from datetime import datetime, timezone

    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker:8001")
    rec_before = await registry.get(worker_id)
    ts_before = rec_before.last_heartbeat_at

    await asyncio.sleep(0.01)  # Small delay
    success = await registry.heartbeat(worker_id, "in_progress", task_id="task-abc")
    assert success is True
    rec_after = await registry.get(worker_id)
    assert rec_after.last_heartbeat_at >= ts_before
    assert rec_after.status == "in_progress"
    assert rec_after.current_task_id == "task-abc"


@pytest.mark.asyncio
async def test_heartbeat_unknown_worker_returns_false():
    registry = WorkerRegistry()
    success = await registry.heartbeat("nonexistent-id", "free")
    assert success is False


@pytest.mark.asyncio
async def test_set_free_clears_task_and_status():
    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker:8001")
    await registry.assign_task(worker_id, "task-123")
    await registry.set_free(worker_id)
    rec = await registry.get(worker_id)
    assert rec.status == "free"
    assert rec.current_task_id is None


@pytest.mark.asyncio
async def test_get_all_returns_all_workers():
    registry = WorkerRegistry()
    await registry.register("agent_a", "http://worker1:8001")
    await registry.register("agent_b", "http://worker2:8001")
    all_workers = await registry.get_all()
    assert len(all_workers) == 2
