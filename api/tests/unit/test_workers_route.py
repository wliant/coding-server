"""Tests for GET /workers endpoint (controller proxy)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_workers_returns_list_when_controller_reachable():
    """GET /workers proxies to controller and returns worker list."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from api.routes.workers import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)

    now = datetime.now(timezone.utc).isoformat()
    mock_workers = [
        {
            "worker_id": "worker-abc",
            "agent_type": "simple_crewai_pair_agent",
            "worker_url": "http://worker1:8001",
            "status": "free",
            "current_task_id": None,
            "registered_at": now,
            "last_heartbeat_at": now,
        }
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_workers
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.get("/workers")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["worker_id"] == "worker-abc"
    assert data[0]["status"] == "free"


@pytest.mark.asyncio
async def test_get_workers_returns_503_when_controller_unreachable():
    """GET /workers returns 503 when controller is not reachable."""
    import httpx
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from api.routes.workers import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.get("/workers")

    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_get_workers_returns_empty_list():
    """GET /workers returns [] when no workers registered."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from api.routes.workers import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.get("/workers")

    assert resp.status_code == 200
    assert resp.json() == []
