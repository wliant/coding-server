"""Tests for worker POST /push endpoint."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from worker.routes import make_router


def _make_app() -> tuple[FastAPI, TestClient]:
    app = FastAPI()
    router = make_router(work_dir_base="/tmp/test-work", db_session_factory=None)
    app.include_router(router)
    return app, TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_worker_state():
    from worker import routes
    routes._state.status = "free"
    routes._state.task_id = None
    routes._state.error_message = None
    routes._state.git_url = None
    routes._state.github_token = None
    routes._state.work_dir_path = None
    yield


def test_push_rejected_when_in_progress():
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


def test_push_returns_branch_name_and_remote_url_on_success():
    from worker import routes
    task_id = str(uuid.uuid4())
    routes._state.status = "completed"
    routes._state.task_id = task_id
    routes._state.git_url = "https://github.com/org/repo.git"
    routes._state.github_token = ""
    routes._state.work_dir_path = "/tmp/test"

    _, client = _make_app()

    with patch("worker.routes.asyncio.to_thread", new=AsyncMock(return_value=("main", "https://github.com/org/repo.git"))):
        resp = client.post("/push", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["branch_name"] == "main"
    assert data["remote_url"] == "https://github.com/org/repo.git"
    assert "pushed_at" in data


def test_push_returns_502_when_git_push_fails():
    from worker import routes
    routes._state.status = "completed"
    routes._state.git_url = "https://github.com/org/repo.git"
    routes._state.github_token = ""
    routes._state.work_dir_path = "/tmp/test"

    _, client = _make_app()

    with patch("worker.routes.asyncio.to_thread", new=AsyncMock(side_effect=Exception("Push rejected"))):
        resp = client.post("/push", json={})

    assert resp.status_code == 502


def test_push_uses_git_url_from_request_body_when_provided():
    from worker import routes
    routes._state.status = "completed"
    routes._state.git_url = None
    routes._state.github_token = ""
    routes._state.work_dir_path = "/tmp/test"

    _, client = _make_app()

    with patch("worker.routes.asyncio.to_thread", new=AsyncMock(return_value=("feature", "https://github.com/org/repo.git"))):
        resp = client.post("/push", json={"git_url": "https://github.com/org/repo.git"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["remote_url"] == "https://github.com/org/repo.git"
