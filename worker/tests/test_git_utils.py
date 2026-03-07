"""Unit tests for worker.git_utils."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from worker.git_utils import clone_repository, inject_github_token


# --- inject_github_token ---


def test_inject_github_token_transforms_https_github_url():
    result = inject_github_token("https://github.com/org/repo.git", "ghp_token")
    assert result == "https://ghp_token@github.com/org/repo.git"


def test_inject_github_token_leaves_ssh_url_unchanged():
    url = "git@github.com:org/repo.git"
    assert inject_github_token(url, "ghp_token") == url


def test_inject_github_token_leaves_non_github_https_unchanged():
    url = "https://gitlab.com/org/repo.git"
    assert inject_github_token(url, "ghp_token") == url


def test_inject_github_token_empty_token_returns_url_unchanged():
    url = "https://github.com/org/repo.git"
    assert inject_github_token(url, "") == url


# --- clone_repository ---


def test_clone_repository_clones_into_path(tmp_path):
    with patch("git.Repo.clone_from") as mock_clone:
        clone_repository("https://github.com/org/repo.git", tmp_path)
        mock_clone.assert_called_once_with("https://github.com/org/repo.git", tmp_path)


def test_clone_repository_with_branch_clones_with_branch(tmp_path):
    with patch("git.Repo.clone_from") as mock_clone:
        clone_repository("https://github.com/org/repo.git", tmp_path, branch="feature/x")
        mock_clone.assert_called_once_with(
            "https://github.com/org/repo.git", tmp_path, branch="feature/x"
        )


def test_clone_repository_falls_back_when_branch_not_found(tmp_path):
    import git

    mock_repo = MagicMock()
    mock_head = MagicMock()
    mock_repo.create_head.return_value = mock_head

    with patch("git.Repo.clone_from") as mock_clone:
        mock_clone.side_effect = [
            git.GitCommandError("clone", "branch not found"),
            mock_repo,
        ]
        clone_repository("https://github.com/org/repo.git", tmp_path, branch="new-branch")

    assert mock_clone.call_count == 2
    mock_repo.create_head.assert_called_once_with("new-branch")
    mock_head.checkout.assert_called_once()


def test_clone_repository_raises_on_clone_failure(tmp_path):
    import git

    with patch("git.Repo.clone_from", side_effect=git.GitCommandError("clone", "fatal error")):
        with pytest.raises(git.GitCommandError):
            clone_repository("https://github.com/org/repo.git", tmp_path)


def test_clone_repository_injects_token(tmp_path):
    with patch("git.Repo.clone_from") as mock_clone:
        clone_repository(
            "https://github.com/org/repo.git",
            tmp_path,
            github_token="ghp_secret",
        )
        mock_clone.assert_called_once_with(
            "https://ghp_secret@github.com/org/repo.git", tmp_path
        )
