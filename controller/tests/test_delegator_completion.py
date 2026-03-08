"""Tests for heartbeat-based task completion processing."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from controller.delegator import process_task_completion
from controller.registry import WorkerRegistry


@pytest.mark.asyncio
async def test_completion_updates_db_status_to_completed():
    """process_task_completion sets job status to 'completed' in DB."""
    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker1:8001")
    task_id = str(uuid.uuid4())
    await registry.assign_task(worker_id, task_id)

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await process_task_completion(
        db=db,
        registry=registry,
        worker_id=worker_id,
        task_id=task_id,
        status="completed",
        error_message=None,
    )

    db.execute.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_completion_updates_db_status_to_failed():
    """process_task_completion sets job status to 'failed' with error_message in DB."""
    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker1:8001")
    task_id = str(uuid.uuid4())
    await registry.assign_task(worker_id, task_id)

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await process_task_completion(
        db=db,
        registry=registry,
        worker_id=worker_id,
        task_id=task_id,
        status="failed",
        error_message="Agent crashed with OOM",
    )

    db.execute.assert_called_once()
    db.commit.assert_called_once()
    # Verify the error_message was included in the update call
    call_args = db.execute.call_args
    stmt = call_args[0][0]
    # The stmt is a SQLAlchemy update; the values dict should include error_message
    compiled = stmt.compile()
    assert "error_message" in str(compiled)


@pytest.mark.asyncio
async def test_heartbeat_with_completed_status_triggers_completion():
    """Heartbeat POST with status=completed calls on_completion_callback."""
    from fastapi.testclient import TestClient
    from controller.app import create_app

    completion_calls = []

    async def on_completion(**kwargs):
        completion_calls.append(kwargs)

    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker1:8001")
    task_id = str(uuid.uuid4())
    await registry.assign_task(worker_id, task_id)

    app = create_app(registry=registry, on_completion_callback=on_completion)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post(
        f"/workers/{worker_id}/heartbeat",
        json={"status": "completed", "task_id": task_id, "error_message": None},
    )
    assert resp.status_code == 200
    assert resp.json()["acknowledged"] is True
    assert len(completion_calls) == 1
    assert completion_calls[0]["status"] == "completed"
    assert completion_calls[0]["task_id"] == task_id


@pytest.mark.asyncio
async def test_heartbeat_with_failed_status_triggers_completion():
    """Heartbeat POST with status=failed calls on_completion_callback."""
    from fastapi.testclient import TestClient
    from controller.app import create_app

    completion_calls = []

    async def on_completion(**kwargs):
        completion_calls.append(kwargs)

    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker1:8001")
    task_id = str(uuid.uuid4())
    await registry.assign_task(worker_id, task_id)

    app = create_app(registry=registry, on_completion_callback=on_completion)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post(
        f"/workers/{worker_id}/heartbeat",
        json={"status": "failed", "task_id": task_id, "error_message": "Something broke"},
    )
    assert resp.status_code == 200
    assert len(completion_calls) == 1
    assert completion_calls[0]["status"] == "failed"
    assert completion_calls[0]["error_message"] == "Something broke"


@pytest.mark.asyncio
async def test_heartbeat_with_in_progress_status_does_not_trigger_completion():
    """Heartbeat POST with status=in_progress does NOT call on_completion_callback."""
    from fastapi.testclient import TestClient
    from controller.app import create_app

    completion_calls = []

    async def on_completion(**kwargs):
        completion_calls.append(kwargs)

    registry = WorkerRegistry()
    worker_id = await registry.register("simple_crewai_pair_agent", "http://worker1:8001")
    task_id = str(uuid.uuid4())

    app = create_app(registry=registry, on_completion_callback=on_completion)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post(
        f"/workers/{worker_id}/heartbeat",
        json={"status": "in_progress", "task_id": task_id, "error_message": None},
    )
    assert resp.status_code == 200
    assert len(completion_calls) == 0


@pytest.mark.asyncio
async def test_heartbeat_unknown_worker_returns_404():
    """Heartbeat for unknown worker returns 404."""
    from fastapi.testclient import TestClient
    from controller.app import create_app

    registry = WorkerRegistry()
    app = create_app(registry=registry)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post(
        "/workers/nonexistent-id/heartbeat",
        json={"status": "in_progress", "task_id": None, "error_message": None},
    )
    assert resp.status_code == 404
