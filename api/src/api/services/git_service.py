"""Git push service for the API.

Uses gitpython to open/initialize a local git repo and force-push a named
branch to a remote URL. Avoids subprocess shell injection.
"""
import logging
from datetime import datetime, timezone

import git

from api.schemas.task import PushResponse

logger = logging.getLogger(__name__)


def push_working_directory_to_remote(
    work_dir_path: str,
    remote_url: str,
    branch_name: str,
) -> PushResponse:
    """Force-push the working directory as a named branch to the remote URL.

    Steps:
    1. Open (or init) the git repo at work_dir_path
    2. Stage all changes and create a commit if the working tree is dirty
    3. Create or reset the branch to HEAD
    4. Force-push to remote_url

    Args:
        work_dir_path: Absolute path to the working directory
        remote_url: Remote git repository URL (SSH or HTTPS)
        branch_name: Branch name to create/push (e.g. "task/abc12345")

    Returns:
        PushResponse with branch_name, remote_url, and pushed_at timestamp

    Raises:
        git.GitCommandError: If the push fails (caller maps to HTTP 502)
        git.InvalidGitRepositoryError: If work_dir_path is not accessible
    """
    logger.info(
        "git_push_starting",
        extra={
            "event": "git_push_starting",
            "work_dir": work_dir_path,
            "remote_url": remote_url,
            "branch": branch_name,
        },
    )

    try:
        repo = git.Repo(work_dir_path)
    except git.InvalidGitRepositoryError:
        repo = git.Repo.init(work_dir_path)

    # Stage all changes and commit if there's anything to commit
    if repo.is_dirty(untracked_files=True):
        repo.git.add(A=True)
        repo.index.commit(f"feat: {branch_name}")

    # Create or reset the target branch at HEAD
    if branch_name in repo.heads:
        branch = repo.heads[branch_name]
        branch.set_commit(repo.head.commit)
    else:
        branch = repo.create_head(branch_name)

    # Configure or replace the remote
    remote_name = "push_target"
    if remote_name in [r.name for r in repo.remotes]:
        repo.delete_remote(remote_name)
    remote = repo.create_remote(remote_name, remote_url)

    # Force-push the branch
    push_info = remote.push(refspec=f"{branch_name}:{branch_name}", force=True)
    for info in push_info:
        if info.flags & git.PushInfo.ERROR:
            raise git.GitCommandError("push", f"Push failed: {info.summary}")

    pushed_at = datetime.now(timezone.utc)

    logger.info(
        "git_push_succeeded",
        extra={
            "event": "git_push_succeeded",
            "branch": branch_name,
            "remote_url": remote_url,
        },
    )

    return PushResponse(
        branch_name=branch_name,
        remote_url=remote_url,
        pushed_at=pushed_at,
    )
