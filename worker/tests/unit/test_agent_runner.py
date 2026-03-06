"""Unit tests for worker.agent_runner — written FIRST per TDD (Constitution II).

Tests run against SQLite in-memory DB via the db_session fixture.
The CodingAgent is fully mocked — no real LLM calls are made.
All tests should FAIL until agent_runner.py is implemented.
"""
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from worker.models import Job, Project


async def _seed_job_with_project(db_session, project_name: str | None = "test-project") -> tuple[Job, Project]:
    """Helper: seed a project + pending job."""
    project = Project(
        name=project_name,
        source_type="new",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Add a hello world function",
        status="in_progress",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(project)
    return job, project


async def test_run_coding_agent_success_creates_work_directory_record(db_session, tmp_path):
    """Successful agent run creates a WorkDirectory DB record with the correct path."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session)
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        LLM_PROVIDER="ollama",
        LLM_MODEL="qwen2.5-coder:7b",
    )

    mock_result = MagicMock()
    mock_result.error = None

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        MockCodingAgent.return_value.run.return_value = mock_result
        success, error_msg = await run_coding_agent(db_session, job, project, settings)

    assert success is True
    assert error_msg is None

    # Verify WorkDirectory record was created
    from sqlalchemy import select
    from worker.models import WorkDirectory
    result = await db_session.execute(
        select(WorkDirectory).where(WorkDirectory.job_id == job.id)
    )
    work_dir = result.scalar_one_or_none()
    assert work_dir is not None
    expected_path = str(tmp_path / str(job.id))
    assert work_dir.path == expected_path


async def test_run_coding_agent_work_directory_path_equals_work_parent_slash_job_id(db_session, tmp_path):
    """Working directory path is exactly {AGENT_WORK_PARENT}/{job_id}."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session)
    work_parent = str(tmp_path)
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=work_parent,
        LLM_PROVIDER="ollama",
        LLM_MODEL="qwen2.5-coder:7b",
    )

    mock_result = MagicMock()
    mock_result.error = None

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        MockCodingAgent.return_value.run.return_value = mock_result
        await run_coding_agent(db_session, job, project, settings)

    expected_path = str(Path(work_parent) / str(job.id))
    from sqlalchemy import select
    from worker.models import WorkDirectory
    result = await db_session.execute(
        select(WorkDirectory).where(WorkDirectory.job_id == job.id)
    )
    work_dir = result.scalar_one()
    assert work_dir.path == expected_path


async def test_run_coding_agent_exception_returns_error_result(db_session, tmp_path):
    """Agent exception returns (False, error_message) without crashing."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session)
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        LLM_PROVIDER="ollama",
        LLM_MODEL="qwen2.5-coder:7b",
    )

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        MockCodingAgent.return_value.run.side_effect = RuntimeError("LLM unavailable")
        success, error_msg = await run_coding_agent(db_session, job, project, settings)

    assert success is False
    assert error_msg is not None
    assert "LLM unavailable" in error_msg


async def test_run_coding_agent_uses_project_name_as_agent_project_name(db_session, tmp_path):
    """CodingAgent is invoked with project_name from Project.name."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session, project_name="my-project")
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        LLM_PROVIDER="ollama",
        LLM_MODEL="qwen2.5-coder:7b",
    )

    mock_result = MagicMock()
    mock_result.error = None

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        with patch("worker.agent_runner.CodingAgentConfig") as MockConfig:
            MockCodingAgent.return_value.run.return_value = mock_result
            await run_coding_agent(db_session, job, project, settings)

    call_kwargs = MockConfig.call_args.kwargs
    assert call_kwargs.get("project_name") == "my-project"


async def test_run_coding_agent_uses_job_id_short_when_project_name_is_none(db_session, tmp_path):
    """When Project.name is None, agent project_name falls back to str(job.id)[:8]."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session, project_name=None)
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        LLM_PROVIDER="ollama",
        LLM_MODEL="qwen2.5-coder:7b",
    )

    mock_result = MagicMock()
    mock_result.error = None

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        with patch("worker.agent_runner.CodingAgentConfig") as MockConfig:
            MockCodingAgent.return_value.run.return_value = mock_result
            await run_coding_agent(db_session, job, project, settings)

    call_kwargs = MockConfig.call_args.kwargs
    assert call_kwargs.get("project_name") == str(job.id)[:8]
