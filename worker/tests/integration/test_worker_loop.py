"""Integration test for the full worker poll → claim → execute → complete cycle.

Written FIRST per TDD (Constitution II).
The CodingAgent is mocked so no real LLM calls are made.
Tests should FAIL until worker.py main_loop() is implemented.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from worker.models import Base, Job, Project, WorkDirectory


@pytest.fixture
async def memory_db():
    """SQLite in-memory engine + session factory for integration tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _seed_pending_job(session: AsyncSession, requirement: str = "Build X") -> tuple[Job, Project]:
    """Insert a project + pending job, return both."""
    project = Project(name="integ-project", source_type="new", status="active")
    session.add(project)
    await session.flush()

    job = Job(
        project_id=project.id,
        requirement=requirement,
        status="pending",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    await session.refresh(project)
    return job, project


async def test_single_poll_cycle_claims_and_completes_pending_job(memory_db, tmp_path):
    """One poll iteration: Pending → In Progress → Completed, WorkDirectory created."""
    from worker.worker import _run_one_poll_cycle
    from worker.config import Settings

    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        POLL_INTERVAL_SECONDS=5,
        LEASE_TTL_SECONDS=300,
        LEASE_RENEWAL_INTERVAL_SECONDS=120,
        LLM_PROVIDER="ollama",
        LLM_MODEL="qwen2.5-coder:7b",
    )

    async with memory_db() as session:
        job, project = await _seed_pending_job(session)
        job_id = job.id

    worker_id = str(uuid.uuid4())
    mock_result = MagicMock()
    mock_result.error = None

    with patch("worker.agent_runner.CodingAgent") as MockAgent:
        MockAgent.return_value.run.return_value = mock_result
        async with memory_db() as session:
            processed = await _run_one_poll_cycle(session, worker_id, settings)

    assert processed is True

    # Verify final state in DB
    async with memory_db() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        final_job = result.scalar_one()
        assert final_job.status == "completed"
        assert final_job.lease_holder is None
        assert final_job.lease_expires_at is None
        assert final_job.completed_at is not None

        wd_result = await session.execute(
            select(WorkDirectory).where(WorkDirectory.job_id == job_id)
        )
        work_dir = wd_result.scalar_one()
        assert work_dir is not None


async def test_single_poll_cycle_sets_failed_on_agent_exception(memory_db, tmp_path):
    """When agent raises, the job transitions to Failed with error_message."""
    from worker.worker import _run_one_poll_cycle
    from worker.config import Settings

    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        POLL_INTERVAL_SECONDS=5,
        LEASE_TTL_SECONDS=300,
        LEASE_RENEWAL_INTERVAL_SECONDS=120,
        LLM_PROVIDER="ollama",
        LLM_MODEL="qwen2.5-coder:7b",
    )

    async with memory_db() as session:
        job, _ = await _seed_pending_job(session)
        job_id = job.id

    worker_id = str(uuid.uuid4())

    with patch("worker.agent_runner.CodingAgent") as MockAgent:
        MockAgent.return_value.run.side_effect = RuntimeError("agent crashed")
        async with memory_db() as session:
            processed = await _run_one_poll_cycle(session, worker_id, settings)

    async with memory_db() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        final_job = result.scalar_one()
        assert final_job.status == "failed"
        assert final_job.error_message is not None
        assert final_job.lease_holder is None


async def test_single_poll_cycle_returns_false_when_no_pending_jobs(memory_db, tmp_path):
    """poll cycle returns False when there are no Pending jobs."""
    from worker.worker import _run_one_poll_cycle
    from worker.config import Settings

    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        POLL_INTERVAL_SECONDS=5,
        LEASE_TTL_SECONDS=300,
        LEASE_RENEWAL_INTERVAL_SECONDS=120,
    )

    worker_id = str(uuid.uuid4())
    async with memory_db() as session:
        processed = await _run_one_poll_cycle(session, worker_id, settings)

    assert processed is False
