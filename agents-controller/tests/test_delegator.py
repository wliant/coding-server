"""Tests for controller delegation logic."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from controller.delegator import (
    _delegate_pending_tasks,
    _handle_cleaning_up_tasks,
    _reap_unreachable_workers,
    _renew_active_leases,
    process_task_completion,
)
from controller.models import Agent, Job, Project
from controller.registry import WorkerRecord, WorkerRegistry


def _make_worker_record(
    worker_id: str = None,
    agent_type: str = "simple_crewai_pair_agent",
    worker_url: str = "http://worker1:8001",
    status: str = "free",
    last_heartbeat_at: datetime = None,
    current_task_id: str = None,
) -> WorkerRecord:
    now = datetime.now(timezone.utc)
    return WorkerRecord(
        worker_id=worker_id or str(uuid.uuid4()),
        agent_type=agent_type,
        worker_url=worker_url,
        status=status,
        last_heartbeat_at=last_heartbeat_at or now,
        registered_at=now,
        current_task_id=current_task_id,
    )


def _make_job(
    status: str = "pending",
    agent_type: str = "simple_crewai_pair_agent",
    assigned_worker_id: str = None,
    assigned_worker_url: str = None,
) -> tuple[Job, Project, Agent]:
    job = MagicMock(spec=Job)
    job.id = uuid.uuid4()
    job.status = status
    job.requirement = "Write a hello world script"
    job.branch = None
    job.assigned_worker_id = assigned_worker_id
    job.assigned_worker_url = assigned_worker_url
    job.project_id = uuid.uuid4()

    project = MagicMock(spec=Project)
    project.id = job.project_id
    project.git_url = None

    agent = MagicMock(spec=Agent)
    agent.identifier = agent_type

    return job, project, agent


# ---------------------------------------------------------------------------
# _reap_unreachable_workers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reap_marks_stale_worker_unreachable():
    registry = WorkerRegistry()
    old_time = datetime.now(timezone.utc) - timedelta(seconds=120)
    worker_id = await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    # Override last_heartbeat_at to be stale
    registry._workers[worker_id].last_heartbeat_at = old_time

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()

    await _reap_unreachable_workers(registry, db, timeout_seconds=60)

    rec = await registry.get(worker_id)
    assert rec.status == "unreachable"


@pytest.mark.asyncio
async def test_reap_resets_in_progress_task_to_pending():
    registry = WorkerRegistry()
    task_id = str(uuid.uuid4())
    old_time = datetime.now(timezone.utc) - timedelta(seconds=120)
    worker_id = await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    registry._workers[worker_id].last_heartbeat_at = old_time
    registry._workers[worker_id].status = "in_progress"
    registry._workers[worker_id].current_task_id = task_id

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _reap_unreachable_workers(registry, db, timeout_seconds=60)

    # db.execute should have been called to reset the task
    db.execute.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_reap_does_not_touch_recently_heartbeating_workers():
    registry = WorkerRegistry()
    worker_id = await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    # Worker heartbeated just now (default) — not stale

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _reap_unreachable_workers(registry, db, timeout_seconds=60)

    db.execute.assert_not_called()
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# _renew_active_leases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_renew_leases_extends_in_progress_worker_lease():
    registry = WorkerRegistry()
    task_id = str(uuid.uuid4())
    worker_id = await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    await registry.assign_task(worker_id, task_id)

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _renew_active_leases(registry, db, lease_ttl_seconds=300)

    db.execute.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_renew_leases_skips_free_workers():
    registry = WorkerRegistry()
    await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    # Worker stays free (no assign_task)

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await _renew_active_leases(registry, db, lease_ttl_seconds=300)

    db.execute.assert_not_called()
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# _delegate_pending_tasks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delegate_claims_task_and_posts_to_worker():
    registry = WorkerRegistry()
    worker_id = await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")

    job, project, agent = _make_job(status="pending")

    db = AsyncMock(spec=AsyncSession)
    # First execute returns pending jobs, second returns claimed row
    mock_result_jobs = MagicMock()
    mock_result_jobs.all.return_value = [(job, project, agent)]
    mock_claimed = MagicMock()
    mock_claimed.fetchone.return_value = (job.id,)
    db.execute = AsyncMock(side_effect=[mock_result_jobs, mock_claimed])
    db.commit = AsyncMock()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("controller.delegator._fetch_llm_config", new_callable=AsyncMock) as mock_llm, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_llm.return_value = {"provider": "ollama", "model": "qwen2.5-coder:7b", "temperature": 0.2}
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _delegate_pending_tasks(registry, db, lease_ttl_seconds=300)

    # Should have called post on the worker URL
    mock_client_instance.post.assert_called_once()
    call_args = mock_client_instance.post.call_args
    assert "http://worker1:8001/work" in call_args[0][0]


@pytest.mark.asyncio
async def test_delegate_skips_when_no_free_worker():
    registry = WorkerRegistry()
    # Register a worker but mark it in_progress
    worker_id = await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    await registry.assign_task(worker_id, str(uuid.uuid4()))

    job, project, agent = _make_job(status="pending")

    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.all.return_value = [(job, project, agent)]
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    with patch("controller.delegator._fetch_llm_config", new_callable=AsyncMock) as mock_llm, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_llm.return_value = {}
        mock_client_instance = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _delegate_pending_tasks(registry, db, lease_ttl_seconds=300)

    # No HTTP call should have been made (no free worker)
    mock_client_instance.post.assert_not_called()


@pytest.mark.asyncio
async def test_delegate_rolls_back_claim_when_worker_post_fails():
    registry = WorkerRegistry()
    await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")

    job, project, agent = _make_job(status="pending")

    db = AsyncMock(spec=AsyncSession)
    mock_result_jobs = MagicMock()
    mock_result_jobs.all.return_value = [(job, project, agent)]
    mock_claimed = MagicMock()
    mock_claimed.fetchone.return_value = (job.id,)
    # execute calls: 1=select pending, 2=update claim, 3=rollback update
    db.execute = AsyncMock(side_effect=[mock_result_jobs, mock_claimed, MagicMock()])
    db.commit = AsyncMock()

    with patch("controller.delegator._fetch_llm_config", new_callable=AsyncMock) as mock_llm, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_llm.return_value = {"provider": "ollama", "model": "test", "temperature": 0.2}
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(side_effect=Exception("connection refused"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _delegate_pending_tasks(registry, db, lease_ttl_seconds=300)

    # Rollback execute should have been called (3 total: select, claim update, rollback update)
    assert db.execute.call_count == 3


# ---------------------------------------------------------------------------
# process_task_completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_task_completion_updates_db_on_completed():
    registry = WorkerRegistry()
    worker_id = await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    task_id = str(uuid.uuid4())
    await registry.assign_task(worker_id, task_id)

    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = (uuid.UUID(task_id),)
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    updated = await process_task_completion(
        db=db,
        registry=registry,
        worker_id=worker_id,
        task_id=task_id,
        status="completed",
        error_message=None,
    )

    assert updated is True
    db.execute.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_process_task_completion_updates_db_on_failed():
    registry = WorkerRegistry()
    worker_id = await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    task_id = str(uuid.uuid4())
    await registry.assign_task(worker_id, task_id)

    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = (uuid.UUID(task_id),)
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    updated = await process_task_completion(
        db=db,
        registry=registry,
        worker_id=worker_id,
        task_id=task_id,
        status="failed",
        error_message="Agent crashed",
    )

    assert updated is True
    db.execute.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_process_task_completion_returns_false_when_job_not_in_progress():
    """Returns False when the job is already pending (reaper reset it)."""
    registry = WorkerRegistry()
    worker_id = await registry.register("worker-1", "simple_crewai_pair_agent", "http://worker1:8001")
    task_id = str(uuid.uuid4())

    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None  # 0 rows updated
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    updated = await process_task_completion(
        db=db,
        registry=registry,
        worker_id=worker_id,
        task_id=task_id,
        status="failed",
        error_message="Agent finished but job was already reset",
    )

    assert updated is False
    db.execute.assert_called_once()
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# _handle_cleaning_up_tasks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_cleaning_up_calls_worker_free():
    registry = WorkerRegistry()

    job = MagicMock(spec=Job)
    job.id = uuid.uuid4()
    job.assigned_worker_url = "http://worker1:8001"

    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [job]
    # Second execute is the DB update
    db.execute = AsyncMock(side_effect=[mock_result, MagicMock()])
    db.commit = AsyncMock()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _handle_cleaning_up_tasks(registry, db)

    mock_client_instance.post.assert_called_once_with("http://worker1:8001/free")


@pytest.mark.asyncio
async def test_handle_cleaning_up_leaves_task_on_worker_error():
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
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(side_effect=Exception("worker down"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _handle_cleaning_up_tasks(registry, db)

    # Should still commit (for idempotency) but only executed 1 time (select, no update)
    assert db.execute.call_count == 1
