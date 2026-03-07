"""Unit tests for worker.agent_runner — focusing on clone integration."""
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.models import Job, Project


def _make_job(git_url=None, branch=None):
    job = MagicMock(spec=Job)
    job.id = uuid.uuid4()
    job.requirement = "Build something"
    job.branch = branch
    return job


def _make_project(git_url=None):
    project = MagicMock(spec=Project)
    project.name = "test-project"
    project.git_url = git_url
    return project


def _make_settings():
    settings = MagicMock()
    settings.API_URL = "http://api:8000"
    settings.AGENT_WORK_PARENT = "/agent-work"
    return settings


@pytest.fixture
def db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_agent_settings():
    return {
        "agent.work.path": "",
        "agent.simple_crewai.llm_provider": "ollama",
        "agent.simple_crewai.llm_model": "qwen2.5-coder:7b",
        "agent.simple_crewai.llm_temperature": "0.2",
        "agent.simple_crewai.ollama_base_url": "http://localhost:11434",
        "agent.simple_crewai.openai_api_key": "",
        "agent.simple_crewai.anthropic_api_key": "",
        "github.token": "",
    }


@pytest.mark.asyncio
async def test_run_coding_agent_calls_clone_when_git_url_set(db_session, mock_agent_settings):
    """clone_repository is called with git_url and branch when project has git_url."""
    from worker import agent_runner

    job = _make_job(branch="feature/x")
    project = _make_project(git_url="https://github.com/org/repo.git")
    settings = _make_settings()

    with (
        patch.object(agent_runner, "_fetch_agent_settings", new=AsyncMock(return_value=mock_agent_settings)),
        patch("worker.agent_runner.clone_repository") as mock_clone,
        patch("asyncio.to_thread", new=AsyncMock(return_value=None)) as mock_to_thread,
        patch.object(agent_runner, "CodingAgent", create=True),
        patch.object(agent_runner, "CodingAgentConfig", create=True),
        patch.object(agent_runner, "_resolve_agent_classes") as mock_resolve,
    ):
        mock_config_instance = MagicMock()
        mock_agent_instance = MagicMock()
        mock_agent_instance.run.return_value = MagicMock(error=None)
        MockConfig = MagicMock(return_value=mock_config_instance)
        MockAgent = MagicMock(return_value=mock_agent_instance)
        mock_resolve.return_value = (MockAgent, MockConfig)

        result = await agent_runner.run_coding_agent(db_session, job, project, settings)

        mock_to_thread.assert_called_once()
        call_args = mock_to_thread.call_args
        # First positional arg should be clone_repository (the mock, while patch is active)
        assert call_args.args[0] is agent_runner.clone_repository


@pytest.mark.asyncio
async def test_run_coding_agent_skips_clone_when_no_git_url(db_session, mock_agent_settings):
    """clone_repository is NOT called when project.git_url is None."""
    from worker import agent_runner

    job = _make_job()
    project = _make_project(git_url=None)
    settings = _make_settings()

    with (
        patch.object(agent_runner, "_fetch_agent_settings", new=AsyncMock(return_value=mock_agent_settings)),
        patch("asyncio.to_thread", new=AsyncMock(return_value=None)) as mock_to_thread,
        patch.object(agent_runner, "_resolve_agent_classes") as mock_resolve,
    ):
        mock_config_instance = MagicMock()
        mock_agent_instance = MagicMock()
        mock_agent_instance.run.return_value = MagicMock(error=None)
        MockConfig = MagicMock(return_value=mock_config_instance)
        MockAgent = MagicMock(return_value=mock_agent_instance)
        mock_resolve.return_value = (MockAgent, MockConfig)

        await agent_runner.run_coding_agent(db_session, job, project, settings)

    # to_thread should not have been called with clone_repository
    for call in mock_to_thread.call_args_list:
        assert call.args[0] is not agent_runner.clone_repository


@pytest.mark.asyncio
async def test_run_coding_agent_returns_failure_when_clone_raises(db_session, mock_agent_settings):
    """Returns (False, ...) without calling CodingAgent when clone raises."""
    from worker import agent_runner

    job = _make_job(branch=None)
    project = _make_project(git_url="https://github.com/org/repo.git")
    settings = _make_settings()

    async def mock_to_thread_raises(fn, *args, **kwargs):
        if fn is agent_runner.clone_repository:
            raise RuntimeError("clone failed")
        return None

    with (
        patch.object(agent_runner, "_fetch_agent_settings", new=AsyncMock(return_value=mock_agent_settings)),
        patch("asyncio.to_thread", new=AsyncMock(side_effect=mock_to_thread_raises)),
        patch.object(agent_runner, "_resolve_agent_classes") as mock_resolve,
    ):
        MockConfig = MagicMock()
        MockAgent = MagicMock()
        mock_resolve.return_value = (MockAgent, MockConfig)

        success, error = await agent_runner.run_coding_agent(db_session, job, project, settings)

    assert success is False
    assert "clone failed" in (error or "")
    MockAgent.return_value.run.assert_not_called()


@pytest.mark.asyncio
async def test_run_coding_agent_passes_github_token_to_clone(db_session):
    """github.token from settings is forwarded to clone_repository."""
    from worker import agent_runner

    job = _make_job(branch="main")
    project = _make_project(git_url="https://github.com/org/repo.git")
    settings = _make_settings()

    agent_settings_with_token = {
        "agent.work.path": "",
        "agent.simple_crewai.llm_provider": "ollama",
        "agent.simple_crewai.llm_model": "qwen2.5-coder:7b",
        "agent.simple_crewai.llm_temperature": "0.2",
        "agent.simple_crewai.ollama_base_url": "http://localhost:11434",
        "agent.simple_crewai.openai_api_key": "",
        "agent.simple_crewai.anthropic_api_key": "",
        "github.token": "ghp_test_token",
    }

    captured_kwargs = {}

    async def capture_to_thread(fn, *args, **kwargs):
        if fn is agent_runner.clone_repository:
            captured_kwargs.update(kwargs)
            captured_kwargs["args"] = args
        return None

    with (
        patch.object(agent_runner, "_fetch_agent_settings", new=AsyncMock(return_value=agent_settings_with_token)),
        patch("asyncio.to_thread", new=AsyncMock(side_effect=capture_to_thread)),
        patch.object(agent_runner, "_resolve_agent_classes") as mock_resolve,
    ):
        mock_config_instance = MagicMock()
        mock_agent_instance = MagicMock()
        mock_agent_instance.run.return_value = MagicMock(error=None)
        MockConfig = MagicMock(return_value=mock_config_instance)
        MockAgent = MagicMock(return_value=mock_agent_instance)
        mock_resolve.return_value = (MockAgent, MockConfig)

        await agent_runner.run_coding_agent(db_session, job, project, settings)

    assert captured_kwargs.get("github_token") == "ghp_test_token"
