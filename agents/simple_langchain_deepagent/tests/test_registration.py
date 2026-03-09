"""Tests for worker registration and heartbeat logic."""
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
            controller_url="http://controller:8003",
            agent_type="simple_langchain_deepagent",
            worker_url="http://simple_langchain_deepagent:8004",
        )

    assert worker_id == "my-worker"
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
                controller_url="http://controller:8003",
                agent_type="simple_langchain_deepagent",
                worker_url="http://simple_langchain_deepagent:8004",
            )

    assert worker_id == "my-worker"
    assert call_count == 3
