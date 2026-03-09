"""Tests for Controller REST API routes (TDD)."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from controller.registry import WorkerRegistry


@pytest.fixture
def app_with_registry():
    """Create a test FastAPI app with an isolated registry."""
    from controller.app import create_app
    registry = WorkerRegistry()
    app = create_app(registry=registry)
    return app, registry


def test_health_endpoint(app_with_registry):
    app, _ = app_with_registry
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_register_worker_happy_path(app_with_registry):
    app, registry = app_with_registry
    client = TestClient(app)
    resp = client.post(
        "/workers/register",
        json={"worker_id": "my-worker", "agent_type": "simple_crewai_pair_agent", "worker_url": "http://worker:8001"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["worker_id"] == "my-worker"


def test_register_worker_missing_worker_id(app_with_registry):
    app, _ = app_with_registry
    client = TestClient(app)
    resp = client.post(
        "/workers/register",
        json={"agent_type": "simple_crewai_pair_agent", "worker_url": "http://worker:8001"},
    )
    assert resp.status_code == 422


def test_register_worker_missing_agent_type(app_with_registry):
    app, _ = app_with_registry
    client = TestClient(app)
    resp = client.post("/workers/register", json={"worker_id": "w1", "worker_url": "http://worker:8001"})
    assert resp.status_code == 422


def test_register_worker_missing_worker_url(app_with_registry):
    app, _ = app_with_registry
    client = TestClient(app)
    resp = client.post("/workers/register", json={"worker_id": "w1", "agent_type": "simple_crewai_pair_agent"})
    assert resp.status_code == 422


def test_heartbeat_known_worker(app_with_registry):
    app, registry = app_with_registry
    client = TestClient(app)
    # Register first
    reg_resp = client.post(
        "/workers/register",
        json={"worker_id": "my-worker", "agent_type": "simple_crewai_pair_agent", "worker_url": "http://worker:8001"},
    )
    worker_id = reg_resp.json()["worker_id"]
    # Send heartbeat
    resp = client.post(
        f"/workers/{worker_id}/heartbeat",
        json={"status": "free"},
    )
    assert resp.status_code == 200
    assert resp.json()["acknowledged"] is True


def test_heartbeat_unknown_worker(app_with_registry):
    app, _ = app_with_registry
    client = TestClient(app)
    resp = client.post(
        "/workers/nonexistent-id/heartbeat",
        json={"status": "free"},
    )
    assert resp.status_code == 404


def test_list_workers_empty(app_with_registry):
    app, _ = app_with_registry
    client = TestClient(app)
    resp = client.get("/workers")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_workers_populated(app_with_registry):
    app, registry = app_with_registry
    client = TestClient(app)
    client.post(
        "/workers/register",
        json={"worker_id": "worker-1", "agent_type": "simple_crewai_pair_agent", "worker_url": "http://worker1:8001"},
    )
    client.post(
        "/workers/register",
        json={"worker_id": "worker-2", "agent_type": "other_agent", "worker_url": "http://worker2:8001"},
    )
    resp = client.get("/workers")
    assert resp.status_code == 200
    workers = resp.json()
    assert len(workers) == 2
    agent_types = {w["agent_type"] for w in workers}
    assert "simple_crewai_pair_agent" in agent_types
    assert "other_agent" in agent_types


def test_heartbeat_completion_callback_returns_should_free_false_when_updated():
    """should_free=False when callback returns True (job was in_progress)."""
    from controller.app import create_app
    registry = WorkerRegistry()

    async def callback(**kwargs):
        return True  # Job was updated successfully

    app = create_app(registry=registry, on_completion_callback=callback)
    client = TestClient(app)

    # Register worker
    client.post(
        "/workers/register",
        json={"worker_id": "w1", "agent_type": "simple_crewai_pair_agent", "worker_url": "http://w1:8001"},
    )

    resp = client.post(
        "/workers/w1/heartbeat",
        json={"status": "completed", "task_id": "some-task-id"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["acknowledged"] is True
    assert data["should_free"] is False


def test_heartbeat_completion_callback_returns_should_free_true_when_not_updated():
    """should_free=True when callback returns False (job was already reset to pending)."""
    from controller.app import create_app
    registry = WorkerRegistry()

    async def callback(**kwargs):
        return False  # Job was NOT in_progress — reaper reset it

    app = create_app(registry=registry, on_completion_callback=callback)
    client = TestClient(app)

    # Register worker
    client.post(
        "/workers/register",
        json={"worker_id": "w1", "agent_type": "simple_crewai_pair_agent", "worker_url": "http://w1:8001"},
    )

    resp = client.post(
        "/workers/w1/heartbeat",
        json={"status": "failed", "task_id": "some-task-id"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["acknowledged"] is True
    assert data["should_free"] is True
