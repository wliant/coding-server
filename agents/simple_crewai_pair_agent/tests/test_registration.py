"""Tests for worker registration and heartbeat logic (TDD)."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_register_with_controller_returns_worker_id():
    """Successful registration returns the confirmed worker_id."""
    from worker.registration import register_with_controller

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"worker_id": "my-worker"}
    mock_response.raise_for_status = MagicMock()

    with patch("worker.registration.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        worker_id = await register_with_controller(
            worker_id="my-worker",
            controller_url="http://controller:8002",
            agent_type="simple_crewai_pair_agent",
            worker_url="http://worker:8001",
        )

    assert worker_id == "my-worker"
    # Verify the worker_id was sent in the request payload
    call_args = mock_client.post.call_args
    assert call_args[1]["json"]["worker_id"] == "my-worker"


@pytest.mark.asyncio
async def test_register_retries_on_connection_error():
    """register_with_controller retries on network failures."""
    import httpx
    from worker.registration import register_with_controller

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {"worker_id": "my-worker"}
    success_response.raise_for_status = MagicMock()

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.ConnectError("Connection refused")
        return success_response

    with patch("worker.registration.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=side_effect)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("worker.registration.asyncio.sleep", new=AsyncMock()):
            worker_id = await register_with_controller(
                worker_id="my-worker",
                controller_url="http://controller:8002",
                agent_type="simple_crewai_pair_agent",
                worker_url="http://worker:8001",
            )

    assert worker_id == "my-worker"
    assert call_count == 3


@pytest.mark.asyncio
async def test_heartbeat_calls_on_should_free_when_response_says_so():
    """on_should_free is called when controller responds with should_free=True."""
    from worker.registration import start_heartbeat_loop

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"acknowledged": True, "should_free": True}

    freed = []

    def on_should_free():
        freed.append(True)

    def get_status():
        return {"status": "failed", "task_id": "task-123", "error_message": "oops"}

    # Mock sleep to return immediately on first call, then stop the loop on second call
    sleep_count = 0

    async def mock_sleep(_):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count >= 2:
            raise asyncio.CancelledError()

    with patch("worker.registration.httpx.AsyncClient") as MockClient, \
         patch("worker.registration.asyncio.sleep", side_effect=mock_sleep):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        try:
            await start_heartbeat_loop(
                controller_url="http://controller:8002",
                worker_id="my-worker",
                get_status=get_status,
                agent_type="simple_crewai_pair_agent",
                worker_url="http://worker:8001",
                on_should_free=on_should_free,
            )
        except asyncio.CancelledError:
            pass

    assert len(freed) == 1


@pytest.mark.asyncio
async def test_heartbeat_does_not_call_on_should_free_when_not_needed():
    """on_should_free is NOT called when controller responds with should_free=False."""
    from worker.registration import start_heartbeat_loop

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"acknowledged": True, "should_free": False}

    freed = []

    def on_should_free():
        freed.append(True)

    def get_status():
        return {"status": "free", "task_id": None, "error_message": None}

    sleep_count = 0

    async def mock_sleep(_):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count >= 2:
            raise asyncio.CancelledError()

    with patch("worker.registration.httpx.AsyncClient") as MockClient, \
         patch("worker.registration.asyncio.sleep", side_effect=mock_sleep):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        try:
            await start_heartbeat_loop(
                controller_url="http://controller:8002",
                worker_id="my-worker",
                get_status=get_status,
                agent_type="simple_crewai_pair_agent",
                worker_url="http://worker:8001",
                on_should_free=on_should_free,
            )
        except asyncio.CancelledError:
            pass

    assert len(freed) == 0
