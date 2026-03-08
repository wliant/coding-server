"""Tests for worker REST API routes."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from worker.routes import make_router


def _make_app() -> tuple[FastAPI, TestClient]:
    app = FastAPI()
    router = make_router(work_dir_base="/tmp/test-work", db_session_factory=None)
    app.include_router(router)
    return app, TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_worker_state():
    """Reset global _state before each test."""
    from worker import routes
    routes._state.status = "free"
    routes._state.task_id = None
    routes._state.error_message = None
    routes._state.git_url = None
    routes._state.github_token = None
    routes._state.work_dir_path = None
    yield


def _work_payload(task_id: str | None = None) -> dict:
    return {
        "task_id": task_id or str(uuid.uuid4()),
        "requirements": "Write a hello world script",
        "agent_type": "simple_crewai_pair_agent",
        "git_url": None,
        "branch": None,
        "github_token": None,
        "llm_config": {
            "provider": "ollama",
            "model": "qwen2.5-coder:7b",
            "temperature": 0.2,
            "ollama_base_url": None,
            "openai_api_key": None,
            "anthropic_api_key": None,
        },
    }


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health_returns_ok():
    _, client = _make_app()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------


def test_status_returns_free_initially():
    _, client = _make_app()
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "free"
    assert data["task_id"] is None


# ---------------------------------------------------------------------------
# POST /work
# ---------------------------------------------------------------------------


def test_work_accepted_when_free():
    _, client = _make_app()
    task_id = str(uuid.uuid4())

    with patch("worker.routes.asyncio.create_task") as mock_create_task:
        mock_create_task.return_value = MagicMock()
        resp = client.post("/work", json=_work_payload(task_id))

    assert resp.status_code == 202
    data = resp.json()
    assert data["accepted"] is True
    assert data["task_id"] == task_id


def test_work_rejected_when_already_in_progress():
    from worker import routes
    routes._state.status = "in_progress"
    routes._state.task_id = str(uuid.uuid4())

    _, client = _make_app()
    resp = client.post("/work", json=_work_payload())
    assert resp.status_code == 409


def test_work_sets_state_to_in_progress():
    from worker import routes

    _, client = _make_app()
    task_id = str(uuid.uuid4())

    with patch("worker.routes.asyncio.create_task") as mock_create_task:
        mock_create_task.return_value = MagicMock()
        client.post("/work", json=_work_payload(task_id))

    assert routes._state.status == "in_progress"
    assert routes._state.task_id == task_id


# ---------------------------------------------------------------------------
# POST /free
# ---------------------------------------------------------------------------


def test_free_resets_state_when_completed():
    from worker import routes
    routes._state.status = "completed"
    routes._state.task_id = str(uuid.uuid4())

    _, client = _make_app()
    resp = client.post("/free")
    assert resp.status_code == 200
    assert resp.json()["freed"] is True
    assert routes._state.status == "free"
    assert routes._state.task_id is None


def test_free_rejects_when_in_progress():
    from worker import routes
    routes._state.status = "in_progress"

    _, client = _make_app()
    resp = client.post("/free")
    assert resp.status_code == 409


def test_free_works_when_already_free():
    _, client = _make_app()
    resp = client.post("/free")
    assert resp.status_code == 200
    assert resp.json()["freed"] is True


# ---------------------------------------------------------------------------
# POST /push
# ---------------------------------------------------------------------------


def test_push_rejected_when_not_completed():
    from worker import routes
    routes._state.status = "in_progress"

    _, client = _make_app()
    resp = client.post("/push", json={})
    assert resp.status_code == 409


def test_push_rejected_when_no_git_url():
    from worker import routes
    routes._state.status = "completed"
    routes._state.git_url = None
    routes._state.work_dir_path = "/tmp/test"

    _, client = _make_app()
    resp = client.post("/push", json={})
    assert resp.status_code == 422
