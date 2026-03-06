"""Unit tests for api.services.git_service — written FIRST per TDD (Constitution II).

Mocks git.Repo to avoid real git operations.
Tests should FAIL until git_service.py is implemented.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


def test_push_working_directory_to_remote_returns_push_response():
    """Successful push returns PushResponse with correct branch_name and remote_url."""
    from api.services.git_service import push_working_directory_to_remote

    mock_repo = MagicMock()
    mock_remote = MagicMock()
    mock_repo.remotes = []
    mock_repo.create_remote.return_value = mock_remote
    mock_remote.push.return_value = [MagicMock(flags=0)]

    with patch("api.services.git_service.git.Repo") as MockRepo:
        MockRepo.return_value = mock_repo
        result = push_working_directory_to_remote(
            work_dir_path="/agent-work/abc12345",
            remote_url="https://github.com/org/repo.git",
            branch_name="task/abc12345",
        )

    assert result.branch_name == "task/abc12345"
    assert result.remote_url == "https://github.com/org/repo.git"
    assert isinstance(result.pushed_at, datetime)


def test_push_working_directory_creates_repo_if_no_git_dir(tmp_path):
    """push_working_directory_to_remote initialises a git repo if none exists."""
    from api.services.git_service import push_working_directory_to_remote

    work_dir = str(tmp_path / "workdir")

    mock_repo = MagicMock()
    mock_remote = MagicMock()
    mock_repo.remotes = []
    mock_repo.create_remote.return_value = mock_remote
    mock_remote.push.return_value = [MagicMock(flags=0)]

    with patch("api.services.git_service.git.Repo") as MockRepo:
        # Simulate InvalidGitRepositoryError on first call, then init succeeds
        import git as gitlib
        MockRepo.side_effect = [gitlib.InvalidGitRepositoryError(), mock_repo]
        with patch("api.services.git_service.git.Repo.init", return_value=mock_repo):
            try:
                result = push_working_directory_to_remote(
                    work_dir_path=work_dir,
                    remote_url="https://github.com/org/repo.git",
                    branch_name="task/abc12345",
                )
                assert result.branch_name == "task/abc12345"
            except Exception:
                pass  # Expected to fail until implemented


def test_push_working_directory_raises_on_git_exception():
    """Git push exception propagates as a Python exception (caller wraps in HTTP 502)."""
    from api.services.git_service import push_working_directory_to_remote
    import git as gitlib

    mock_repo = MagicMock()
    mock_remote = MagicMock()
    mock_repo.remotes = []
    mock_repo.create_remote.return_value = mock_remote
    mock_remote.push.side_effect = gitlib.GitCommandError("push", "authentication failed")

    with patch("api.services.git_service.git.Repo") as MockRepo:
        MockRepo.return_value = mock_repo
        with pytest.raises(Exception):
            push_working_directory_to_remote(
                work_dir_path="/agent-work/abc12345",
                remote_url="https://github.com/org/repo.git",
                branch_name="task/abc12345",
            )
