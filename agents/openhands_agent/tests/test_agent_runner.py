"""Unit tests for worker.agent_runner — WorkRequest-based API."""
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.agent_runner import WorkRequest


def _make_request(
    git_url: str | None = None,
    branch: str | None = None,
    github_token: str | None = None,
    llm_config: dict | None = None,
) -> WorkRequest:
    return WorkRequest(
        task_id=str(uuid.uuid4()),
        requirements="Write a hello world script",
        agent_type="openhands_agent",
        work_dir="/agent-work/test",
        git_url=git_url,
        branch=branch,
        github_token=github_token,
        llm_config=llm_config or {"provider": "ollama", "model": "qwen2.5-coder:7b", "temperature": 0.2},
    )


@pytest.mark.asyncio
async def test_run_coding_agent_calls_clone_when_git_url_set():
    """clone_repository is called with git_url and branch when req has git_url."""
    from worker import agent_runner

    req = _make_request(git_url="https://github.com/org/repo.git", branch="feature/x")

    with (
        patch("asyncio.to_thread", new=AsyncMock(return_value=None)) as mock_to_thread,
        patch.object(agent_runner, "_resolve_agent_classes") as mock_resolve,
        patch.object(agent_runner, "_persist_execution_start", new=AsyncMock()),
        patch.object(agent_runner, "_persist_execution_end", new=AsyncMock()),
    ):
        mock_agent_instance = MagicMock()
        mock_agent_instance.run.return_value = MagicMock(summary="done", error=None)
        MockConfig = MagicMock(return_value=MagicMock())
        MockAgent = MagicMock(return_value=mock_agent_instance)
        mock_resolve.return_value = (MockAgent, MockConfig)

        await agent_runner.run_coding_agent(req, db_session_factory=None)

    # asyncio.to_thread should have been called for clone
    mock_to_thread.assert_called_once()
    call_args = mock_to_thread.call_args
    assert call_args.args[0] is agent_runner.clone_repository


@pytest.mark.asyncio
async def test_run_coding_agent_skips_clone_when_no_git_url():
    """clone_repository is NOT called when req.git_url is None."""
    from worker import agent_runner

    req = _make_request(git_url=None)

    with (
        patch("asyncio.to_thread", new=AsyncMock(return_value=None)) as mock_to_thread,
        patch.object(agent_runner, "_resolve_agent_classes") as mock_resolve,
        patch.object(agent_runner, "_persist_execution_start", new=AsyncMock()),
        patch.object(agent_runner, "_persist_execution_end", new=AsyncMock()),
    ):
        mock_agent_instance = MagicMock()
        mock_agent_instance.run.return_value = MagicMock(summary="done")
        MockConfig = MagicMock(return_value=MagicMock())
        MockAgent = MagicMock(return_value=mock_agent_instance)
        mock_resolve.return_value = (MockAgent, MockConfig)

        await agent_runner.run_coding_agent(req, db_session_factory=None)

    # to_thread should not have been called with clone_repository
    for call in mock_to_thread.call_args_list:
        assert call.args[0] is not agent_runner.clone_repository


@pytest.mark.asyncio
async def test_run_coding_agent_returns_failure_when_clone_raises():
    """Returns (False, ...) without calling OpenHandsAgent when clone raises."""
    from worker import agent_runner

    req = _make_request(git_url="https://github.com/org/repo.git")

    async def mock_to_thread_raises(fn, *args, **kwargs):
        if fn is agent_runner.clone_repository:
            raise RuntimeError("clone failed")
        return None

    with (
        patch("asyncio.to_thread", new=AsyncMock(side_effect=mock_to_thread_raises)),
        patch.object(agent_runner, "_resolve_agent_classes") as mock_resolve,
        patch.object(agent_runner, "_persist_execution_start", new=AsyncMock()),
        patch.object(agent_runner, "_persist_execution_end", new=AsyncMock()),
    ):
        MockConfig = MagicMock()
        MockAgent = MagicMock()
        mock_resolve.return_value = (MockAgent, MockConfig)

        success, error = await agent_runner.run_coding_agent(req, db_session_factory=None)

    assert success is False
    assert "clone failed" in (error or "")
    MockAgent.return_value.run.assert_not_called()


@pytest.mark.asyncio
async def test_run_coding_agent_passes_github_token_to_clone():
    """github_token from req is forwarded to clone_repository."""
    from worker import agent_runner

    req = _make_request(
        git_url="https://github.com/org/repo.git",
        branch="main",
        github_token="ghp_test_token",
    )

    captured_kwargs: dict = {}

    async def capture_to_thread(fn, *args, **kwargs):
        if fn is agent_runner.clone_repository:
            captured_kwargs.update(kwargs)
            captured_kwargs["fn_args"] = args
        return None

    with (
        patch("asyncio.to_thread", new=AsyncMock(side_effect=capture_to_thread)),
        patch.object(agent_runner, "_resolve_agent_classes") as mock_resolve,
        patch.object(agent_runner, "_persist_execution_start", new=AsyncMock()),
        patch.object(agent_runner, "_persist_execution_end", new=AsyncMock()),
    ):
        mock_agent_instance = MagicMock()
        mock_agent_instance.run.return_value = MagicMock(summary="done")
        MockConfig = MagicMock(return_value=MagicMock())
        MockAgent = MagicMock(return_value=mock_agent_instance)
        mock_resolve.return_value = (MockAgent, MockConfig)

        await agent_runner.run_coding_agent(req, db_session_factory=None)

    assert captured_kwargs.get("github_token") == "ghp_test_token"


@pytest.mark.asyncio
async def test_run_coding_agent_returns_success():
    """Returns (True, None) on successful agent run."""
    from worker import agent_runner

    req = _make_request()

    with (
        patch.object(agent_runner, "_resolve_agent_classes") as mock_resolve,
        patch.object(agent_runner, "_persist_execution_start", new=AsyncMock()),
        patch.object(agent_runner, "_persist_execution_end", new=AsyncMock()),
    ):
        mock_agent_instance = MagicMock()
        mock_agent_instance.run.return_value = MagicMock(summary="done")
        MockConfig = MagicMock(return_value=MagicMock())
        MockAgent = MagicMock(return_value=mock_agent_instance)
        mock_resolve.return_value = (MockAgent, MockConfig)

        success, error = await agent_runner.run_coding_agent(req, db_session_factory=None)

    assert success is True
    assert error is None


@pytest.mark.asyncio
async def test_run_coding_agent_returns_failure_on_exception():
    """Returns (False, error_msg) when agent raises an exception."""
    from worker import agent_runner

    req = _make_request()

    with (
        patch.object(agent_runner, "_resolve_agent_classes") as mock_resolve,
        patch.object(agent_runner, "_persist_execution_start", new=AsyncMock()),
        patch.object(agent_runner, "_persist_execution_end", new=AsyncMock()),
    ):
        mock_agent_instance = MagicMock()
        mock_agent_instance.run.side_effect = RuntimeError("Something went wrong")
        MockConfig = MagicMock(return_value=MagicMock())
        MockAgent = MagicMock(return_value=mock_agent_instance)
        mock_resolve.return_value = (MockAgent, MockConfig)

        success, error = await agent_runner.run_coding_agent(req, db_session_factory=None)

    assert success is False
    assert "Something went wrong" in (error or "")
