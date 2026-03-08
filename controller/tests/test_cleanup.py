"""Tests for controller cleanup flow (_handle_cleaning_up_tasks)."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from controller.delegator import _handle_cleaning_up_tasks
from controller.models import Job
from controller.registry import WorkerRegistry


@pytest.mark.asyncio
async def test_handle_cleaning_up_calls_worker_free_endpoint():
    """cleaning_up task with assigned_worker_url → POST {worker_url}/free is called."""
    registry = WorkerRegistry()

    job = MagicMock(spec=Job)
    job.id = uuid.uuid4()
    job.assigned_worker_url = "http://worker1:8001"

    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [job]
    db.execute = AsyncMock(side_effect=[mock_result, MagicMock()])
    db.commit = AsyncMock()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _handle_cleaning_up_tasks(registry, db)

    mock_client.post.assert_called_once_with("http://worker1:8001/free")


@pytest.mark.asyncio
async def test_handle_cleaning_up_sets_job_to_cleaned_after_success():
    """After successful /free call, job status is updated to 'cleaned' in DB."""
    registry = WorkerRegistry()

    job = MagicMock(spec=Job)
    job.id = uuid.uuid4()
    job.assigned_worker_url = "http://worker1:8001"

    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [job]
    update_result = MagicMock()
    db.execute = AsyncMock(side_effect=[mock_result, update_result])
    db.commit = AsyncMock()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _handle_cleaning_up_tasks(registry, db)

    # Should have called execute twice: select + update
    assert db.execute.call_count == 2
    db.commit.assert_called_once()

    # Verify the update statement targets 'cleaned' status
    update_call = db.execute.call_args_list[1]
    stmt = update_call[0][0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "cleaned" in compiled


@pytest.mark.asyncio
async def test_handle_cleaning_up_leaves_task_on_worker_error():
    """When /free call fails, job stays in cleaning_up (DB update NOT called)."""
    registry = WorkerRegistry()

    job = MagicMock(spec=Job)
    job.id = uuid.uuid4()
    job.assigned_worker_url = "http://worker1:8001"

    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [job]
    db.execute = AsyncMock(side_effect=[mock_result])
    db.commit = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _handle_cleaning_up_tasks(registry, db)

    # Only the select was executed, no update
    assert db.execute.call_count == 1


@pytest.mark.asyncio
async def test_handle_cleaning_up_no_cleaning_tasks_is_noop():
    """When no cleaning_up tasks exist, no HTTP calls or DB writes happen."""
    registry = WorkerRegistry()

    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _handle_cleaning_up_tasks(registry, db)

    mock_client.post.assert_not_called()
    db.commit.assert_not_called()
