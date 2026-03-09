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


# --- _push_sync ---


def _bare_remote(tmp_path: Path) -> str:
    """Create a local bare git repo and return its file:// URL."""
    import git

    bare = tmp_path / "remote.git"
    git.Repo.init(str(bare), bare=True)
    return bare.as_uri()


def test_push_sync_from_non_git_directory(tmp_path):
    """_push_sync should init, commit, and push even when work_dir has no .git folder."""
    from worker.routes import _push_sync

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (work_dir / "solution.py").write_text("def add(a, b): return a + b\n")

    remote_url = _bare_remote(tmp_path)
    branch, url = _push_sync(str(work_dir), remote_url)

    assert branch  # branch name returned
    assert url == remote_url

    # Verify the commit landed in the bare remote
    import git
    bare = git.Repo(tmp_path / "remote.git")
    commits = list(bare.iter_commits(branch))
    assert len(commits) == 1
    assert "solution.py" in [item.path for item in commits[0].tree.traverse()]


def test_push_sync_from_cloned_repo_with_changes(tmp_path):
    """_push_sync should stage + commit agent changes on an already-cloned repo."""
    import git
    from worker.routes import _push_sync

    remote_url = _bare_remote(tmp_path)

    # Simulate a clone: init a repo, add an initial commit, set remote
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    repo = git.Repo.init(str(work_dir))
    (work_dir / "README.md").write_text("placeholder\n")
    repo.git.add(A=True)
    from git import Actor
    author = Actor("Test", "test@test.com")
    repo.index.commit("init", author=author, committer=author)
    repo.create_remote("origin", remote_url)
    repo.remote("origin").push(refspec="master:master")

    # Agent writes a new file (not committed yet)
    (work_dir / "solution.py").write_text("def add(a, b): return a + b\n")

    branch, _ = _push_sync(str(work_dir), remote_url)

    bare = git.Repo(tmp_path / "remote.git")
    commits = list(bare.iter_commits(branch))
    assert len(commits) == 2  # initial + agent commit
    files_in_latest = [item.path for item in commits[0].tree.traverse()]
    assert "solution.py" in files_in_latest
