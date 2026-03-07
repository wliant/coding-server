"""Unit tests for worker.agent_runner — written FIRST per TDD (Constitution II).

Tests run against SQLite in-memory DB via the db_session fixture.
The CodingAgent and httpx calls are fully mocked — no real LLM or HTTP calls.
All new tests should FAIL until agent_runner.py is updated.
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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


def _make_settings_response(overrides: dict | None = None) -> dict:
    """Default settings API response for tests."""
    defaults = {
        "agent.work.path": "/agent-work",
        "agent.simple_crewai.llm_provider": "ollama",
        "agent.simple_crewai.llm_model": "qwen2.5-coder:7b",
        "agent.simple_crewai.llm_temperature": "0.2",
        "agent.simple_crewai.ollama_base_url": "http://localhost:11434",
        "agent.simple_crewai.openai_api_key": "",
        "agent.simple_crewai.anthropic_api_key": "",
    }
    if overrides:
        defaults.update(overrides)
    return {"settings": defaults}


async def test_run_coding_agent_success_creates_work_directory_record(db_session, tmp_path):
    """Successful agent run creates a WorkDirectory DB record with the correct path."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session)
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        API_URL="http://api:8000",
    )

    mock_result = MagicMock()
    mock_result.error = None
    mock_http_response = MagicMock(spec=httpx.Response)
    # Use empty agent.work.path so the worker falls back to AGENT_WORK_PARENT (tmp_path)
    mock_http_response.json.return_value = _make_settings_response({"agent.work.path": ""})
    mock_http_response.raise_for_status = MagicMock()

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        with patch("worker.agent_runner.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_http_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            MockCodingAgent.return_value.run.return_value = mock_result
            success, error_msg = await run_coding_agent(db_session, job, project, settings)

    assert success is True
    assert error_msg is None

    from sqlalchemy import select
    from worker.models import WorkDirectory
    result = await db_session.execute(
        select(WorkDirectory).where(WorkDirectory.job_id == job.id)
    )
    work_dir = result.scalar_one_or_none()
    assert work_dir is not None
    expected_path = str(tmp_path / str(job.id))
    assert work_dir.path == expected_path


async def test_run_coding_agent_fetches_settings_from_api(db_session, tmp_path):
    """agent_runner calls GET {API_URL}/settings before running the agent."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session)
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        API_URL="http://api:8000",
    )

    mock_result = MagicMock()
    mock_result.error = None
    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.json.return_value = _make_settings_response()
    mock_http_response.raise_for_status = MagicMock()

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        with patch("worker.agent_runner.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_http_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            MockCodingAgent.return_value.run.return_value = mock_result
            await run_coding_agent(db_session, job, project, settings)

    mock_client_instance.get.assert_called_once_with("http://api:8000/settings")


async def test_run_coding_agent_maps_settings_to_config(db_session, tmp_path):
    """Settings API values are correctly mapped to CodingAgentConfig fields."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session, project_name="my-project")
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        API_URL="http://api:8000",
    )

    api_settings = _make_settings_response({
        "agent.simple_crewai.llm_provider": "openai",
        "agent.simple_crewai.llm_model": "gpt-4o",
        "agent.simple_crewai.llm_temperature": "0.5",
        "agent.simple_crewai.openai_api_key": "sk-test",
    })
    mock_result = MagicMock()
    mock_result.error = None
    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.json.return_value = api_settings
    mock_http_response.raise_for_status = MagicMock()

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        with patch("worker.agent_runner.CodingAgentConfig") as MockConfig:
            with patch("worker.agent_runner.httpx.AsyncClient") as MockClient:
                mock_client_instance = AsyncMock()
                mock_client_instance.get = AsyncMock(return_value=mock_http_response)
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
                MockCodingAgent.return_value.run.return_value = mock_result
                await run_coding_agent(db_session, job, project, settings)

    call_kwargs = MockConfig.call_args.kwargs
    assert call_kwargs["llm_provider"] == "openai"
    assert call_kwargs["llm_model"] == "gpt-4o"
    assert call_kwargs["llm_temperature"] == 0.5
    assert call_kwargs["openai_api_key"] == "sk-test"


async def test_run_coding_agent_api_unreachable_fails_job(db_session, tmp_path):
    """If settings API is unreachable, job fails with 'unable to fetch agent settings'."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session)
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        API_URL="http://api:8000",
    )

    with patch("worker.agent_runner.httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        success, error_msg = await run_coding_agent(db_session, job, project, settings)

    assert success is False
    assert error_msg is not None
    assert "unable to fetch agent settings" in error_msg


async def test_run_coding_agent_exception_returns_error_result(db_session, tmp_path):
    """Agent exception returns (False, error_message) without crashing."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session)
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        API_URL="http://api:8000",
    )

    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.json.return_value = _make_settings_response()
    mock_http_response.raise_for_status = MagicMock()

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        with patch("worker.agent_runner.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_http_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
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
        API_URL="http://api:8000",
    )

    mock_result = MagicMock()
    mock_result.error = None
    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.json.return_value = _make_settings_response()
    mock_http_response.raise_for_status = MagicMock()

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        with patch("worker.agent_runner.CodingAgentConfig") as MockConfig:
            with patch("worker.agent_runner.httpx.AsyncClient") as MockClient:
                mock_client_instance = AsyncMock()
                mock_client_instance.get = AsyncMock(return_value=mock_http_response)
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
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
        API_URL="http://api:8000",
    )

    mock_result = MagicMock()
    mock_result.error = None
    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.json.return_value = _make_settings_response()
    mock_http_response.raise_for_status = MagicMock()

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        with patch("worker.agent_runner.CodingAgentConfig") as MockConfig:
            with patch("worker.agent_runner.httpx.AsyncClient") as MockClient:
                mock_client_instance = AsyncMock()
                mock_client_instance.get = AsyncMock(return_value=mock_http_response)
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
                MockCodingAgent.return_value.run.return_value = mock_result
                await run_coding_agent(db_session, job, project, settings)

    call_kwargs = MockConfig.call_args.kwargs
    assert call_kwargs.get("project_name") == str(job.id)[:8]


async def test_run_coding_agent_uses_agent_work_path_from_settings(db_session, tmp_path):
    """When agent.work.path is set in API settings, it is used as the working directory base."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session)
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT="/fallback-should-not-be-used",
        API_URL="http://api:8000",
    )

    mock_result = MagicMock()
    mock_result.error = None
    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.json.return_value = _make_settings_response({"agent.work.path": str(tmp_path)})
    mock_http_response.raise_for_status = MagicMock()

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        with patch("worker.agent_runner.CodingAgentConfig") as MockConfig:
            with patch("worker.agent_runner.httpx.AsyncClient") as MockClient:
                mock_client_instance = AsyncMock()
                mock_client_instance.get = AsyncMock(return_value=mock_http_response)
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
                MockCodingAgent.return_value.run.return_value = mock_result
                await run_coding_agent(db_session, job, project, settings)

    call_kwargs = MockConfig.call_args.kwargs
    expected_work_dir = tmp_path / str(job.id)
    assert call_kwargs["working_directory"] == expected_work_dir


async def test_run_coding_agent_falls_back_to_env_when_work_path_empty(db_session, tmp_path):
    """When agent.work.path is empty, AGENT_WORK_PARENT env var is used."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session)
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        API_URL="http://api:8000",
    )

    mock_result = MagicMock()
    mock_result.error = None
    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.json.return_value = _make_settings_response({"agent.work.path": ""})
    mock_http_response.raise_for_status = MagicMock()

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        with patch("worker.agent_runner.CodingAgentConfig") as MockConfig:
            with patch("worker.agent_runner.httpx.AsyncClient") as MockClient:
                mock_client_instance = AsyncMock()
                mock_client_instance.get = AsyncMock(return_value=mock_http_response)
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
                MockCodingAgent.return_value.run.return_value = mock_result
                await run_coding_agent(db_session, job, project, settings)

    call_kwargs = MockConfig.call_args.kwargs
    expected_work_dir = tmp_path / str(job.id)
    assert call_kwargs["working_directory"] == expected_work_dir


async def test_run_coding_agent_relative_work_path_falls_back_to_env(db_session, tmp_path):
    """When agent.work.path is a relative path (no leading /), AGENT_WORK_PARENT is used."""
    from worker.agent_runner import run_coding_agent
    from worker.config import Settings

    job, project = await _seed_job_with_project(db_session)
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AGENT_WORK_PARENT=str(tmp_path),
        API_URL="http://api:8000",
    )

    mock_result = MagicMock()
    mock_result.error = None
    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.json.return_value = _make_settings_response({"agent.work.path": "agent-work"})
    mock_http_response.raise_for_status = MagicMock()

    with patch("worker.agent_runner.CodingAgent") as MockCodingAgent:
        with patch("worker.agent_runner.CodingAgentConfig") as MockConfig:
            with patch("worker.agent_runner.httpx.AsyncClient") as MockClient:
                mock_client_instance = AsyncMock()
                mock_client_instance.get = AsyncMock(return_value=mock_http_response)
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
                MockCodingAgent.return_value.run.return_value = mock_result
                await run_coding_agent(db_session, job, project, settings)

    # Relative path rejected; falls back to AGENT_WORK_PARENT
    call_kwargs = MockConfig.call_args.kwargs
    expected_work_dir = tmp_path / str(job.id)
    assert call_kwargs["working_directory"] == expected_work_dir
