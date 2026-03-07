"""Git utilities for the worker: token injection and repository cloning."""
from pathlib import Path

import git


def inject_github_token(url: str, token: str) -> str:
    """Inject token into HTTPS GitHub URL. No-op for SSH or non-GitHub URLs."""
    if not token:
        return url
    if url.startswith("https://github.com"):
        return url.replace("https://", f"https://{token}@", 1)
    return url


def clone_repository(
    git_url: str,
    to_path: Path,
    branch: str | None = None,
    github_token: str = "",
) -> None:
    """Clone git_url into to_path, optionally checking out branch.

    If branch doesn't exist remotely, creates it from default branch.
    Raises on clone failure.
    """
    authenticated_url = inject_github_token(git_url, github_token)
    if branch:
        try:
            git.Repo.clone_from(authenticated_url, to_path, branch=branch)
            return
        except git.GitCommandError:
            pass  # Branch not found — clone default then create
        repo = git.Repo.clone_from(authenticated_url, to_path)
        repo.create_head(branch).checkout()
    else:
        git.Repo.clone_from(authenticated_url, to_path)
