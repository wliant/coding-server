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
        json={"agent_type": "simple_crewai_pair_agent", "worker_url": "http://worker:8001"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "worker_id" in data
    assert isinstance(data["worker_id"], str)


def test_register_worker_missing_agent_type(app_with_registry):
    app, _ = app_with_registry
    client = TestClient(app)
    resp = client.post("/workers/register", json={"worker_url": "http://worker:8001"})
    assert resp.status_code == 422


def test_register_worker_missing_worker_url(app_with_registry):
    app, _ = app_with_registry
    client = TestClient(app)
    resp = client.post("/workers/register", json={"agent_type": "simple_crewai_pair_agent"})
    assert resp.status_code == 422


def test_heartbeat_known_worker(app_with_registry):
    app, registry = app_with_registry
    client = TestClient(app)
    # Register first
    reg_resp = client.post(
        "/workers/register",
        json={"agent_type": "simple_crewai_pair_agent", "worker_url": "http://worker:8001"},
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
        json={"agent_type": "simple_crewai_pair_agent", "worker_url": "http://worker1:8001"},
    )
    client.post(
        "/workers/register",
        json={"agent_type": "other_agent", "worker_url": "http://worker2:8001"},
    )
    resp = client.get("/workers")
    assert resp.status_code == 200
    workers = resp.json()
    assert len(workers) == 2
    agent_types = {w["agent_type"] for w in workers}
    assert "simple_crewai_pair_agent" in agent_types
    assert "other_agent" in agent_types
