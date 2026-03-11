"""Worker REST API routes."""
import asyncio
import io
import logging
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class WorkerState:
    status: str = "free"
    task_id: str | None = None
    error_message: str | None = None
    git_url: str | None = None
    github_token: str | None = None
    work_dir_path: str | None = None


# Global mutable state for this worker process
_state = WorkerState()


def get_current_state() -> dict:
    return {
        "status": _state.status,
        "task_id": _state.task_id,
        "error_message": _state.error_message,
    }


def _set_state_free() -> None:
    """Reset state to free. Only acts if worker is not actively running."""
    if _state.status != "in_progress":
        _state.status = "free"
        _state.task_id = None
        _state.error_message = None
        _state.git_url = None
        _state.github_token = None
        _state.work_dir_path = None


class LLMConfig(BaseModel):
    provider: str
    model: str
    temperature: float = 0.2
    ollama_base_url: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


class WorkRequest(BaseModel):
    task_id: str
    requirements: str
    agent_type: str
    git_url: str | None = None
    branch: str | None = None
    github_token: str | None = None
    llm_config: LLMConfig


class WorkAcceptedResponse(BaseModel):
    accepted: bool
    task_id: str


class WorkerStatusResponse(BaseModel):
    status: str
    task_id: str | None = None


class PushRequest(BaseModel):
    git_url: str | None = None
    github_token: str | None = None


class PushResponse(BaseModel):
    branch_name: str
    remote_url: str
    pushed_at: datetime


class FreeResponse(BaseModel):
    freed: bool


def make_router(work_dir_base: str, db_session_factory=None) -> APIRouter:
    r = APIRouter()

    @r.get("/health")
    async def health():
        return {"status": "ok"}

    @r.post("/work", response_model=WorkAcceptedResponse, status_code=202)
    async def issue_work(req: WorkRequest):
        if _state.status != "free":
            raise HTTPException(status_code=409, detail=f"Worker is not free (status: {_state.status})")

        _state.status = "in_progress"
        _state.task_id = req.task_id
        _state.error_message = None
        _state.git_url = req.git_url
        _state.github_token = req.github_token

        work_dir = Path(work_dir_base) / req.task_id
        work_dir.mkdir(parents=True, exist_ok=True)
        _state.work_dir_path = str(work_dir)

        logger.info(
            "work_received",
            extra={
                "event": "work_received",
                "task_id": req.task_id,
                "agent_type": req.agent_type,
                "git_url": req.git_url,
                "has_token": bool(req.github_token),
            },
        )

        # Start execution in background
        asyncio.create_task(_execute_work(req, work_dir, db_session_factory))
        return WorkAcceptedResponse(accepted=True, task_id=req.task_id)

    @r.get("/status", response_model=WorkerStatusResponse)
    async def get_status():
        return WorkerStatusResponse(status=_state.status, task_id=_state.task_id)

    @r.get("/download")
    async def download_work() -> Response:
        """Return the working directory as a zip archive."""
        if not _state.work_dir_path:
            raise HTTPException(status_code=404, detail="No working directory available")
        work_dir = Path(_state.work_dir_path)
        if not work_dir.exists():
            raise HTTPException(status_code=404, detail="Working directory not found")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in work_dir.rglob("*"):
                if file_path.is_file():
                    zf.write(file_path, file_path.relative_to(work_dir))
        buf.seek(0)

        return Response(
            content=buf.read(),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=work.zip"},
        )

    @r.post("/push", response_model=PushResponse)
    async def push_to_remote(req: PushRequest):
        if _state.status != "completed":
            raise HTTPException(status_code=409, detail=f"Worker is not completed (status: {_state.status})")

        effective_git_url = req.git_url or _state.git_url
        if not effective_git_url:
            raise HTTPException(status_code=422, detail="No git_url configured for this task")

        work_dir = _state.work_dir_path
        if not work_dir:
            raise HTTPException(status_code=422, detail="No working directory found")

        try:
            from worker.git_utils import inject_github_token
            # req.github_token takes precedence (API re-fetches from settings on each push)
            token = req.github_token or _state.github_token or ""
            authenticated_url = inject_github_token(effective_git_url, token)
            branch_name, remote_url = await asyncio.to_thread(
                _push_sync, work_dir, authenticated_url
            )
            pushed_at = datetime.now(timezone.utc)
            logger.info(
                "push_succeeded",
                extra={"event": "push_succeeded", "task_id": _state.task_id, "branch": branch_name},
            )
            return PushResponse(branch_name=branch_name, remote_url=effective_git_url, pushed_at=pushed_at)
        except Exception as exc:
            logger.error("push_failed", extra={"event": "push_failed", "error": str(exc)})
            raise HTTPException(status_code=502, detail=f"Push failed: {exc}")

    @r.post("/free", response_model=FreeResponse)
    async def free_worker():
        if _state.status == "in_progress":
            raise HTTPException(status_code=409, detail="Cannot free worker while in_progress")

        work_dir = _state.work_dir_path
        if work_dir:
            p = Path(work_dir)
            if p.exists():
                try:
                    shutil.rmtree(p)
                    logger.info(
                        "cleanup_succeeded",
                        extra={"event": "cleanup_succeeded", "path": work_dir},
                    )
                except Exception as exc:
                    logger.error("cleanup_failed", extra={"event": "cleanup_failed", "error": str(exc)})
                    raise HTTPException(status_code=500, detail=f"Failed to delete working directory: {exc}")

        _state.status = "free"
        _state.task_id = None
        _state.error_message = None
        _state.git_url = None
        _state.github_token = None
        _state.work_dir_path = None

        return FreeResponse(freed=True)

    return r


def _push_sync(work_dir: str, authenticated_url: str) -> tuple[str, str]:
    """Synchronous git push — runs in executor thread.

    Handles two cases:
    - work_dir IS a git repo (cloned at task start): stages uncommitted changes, commits if
      any, then pushes.
    - work_dir is NOT a git repo (no git_url at task start): initialises a new repo, stages
      all agent-written files, creates an initial commit, then pushes.
    """
    import git as gitpython
    from git import Actor

    author = Actor("Coding Agent", "agent@coding-machine.local")

    try:
        repo = gitpython.Repo(work_dir)
    except gitpython.exc.InvalidGitRepositoryError:
        repo = gitpython.Repo.init(work_dir)

    # Stage all new/modified/deleted files
    repo.git.add(A=True)

    # Commit when there are no commits yet (fresh init) or the index differs from HEAD.
    needs_commit = not repo.head.is_valid() or bool(repo.index.diff("HEAD"))
    if needs_commit:
        repo.index.commit(
            "feat: implementation by coding agent",
            author=author,
            committer=author,
        )

    branch_name = repo.active_branch.name

    if "origin" not in [r.name for r in repo.remotes]:
        repo.create_remote("origin", authenticated_url)
    else:
        repo.remote("origin").set_url(authenticated_url)

    repo.remote("origin").push(refspec=f"{branch_name}:{branch_name}")
    return branch_name, authenticated_url


async def _execute_work(req: WorkRequest, work_dir: Path, db_session_factory) -> None:
    """Background task: run agent and update state."""
    from worker.agent_runner import run_coding_agent, WorkRequest as AgentWorkRequest

    agent_req = AgentWorkRequest(
        task_id=req.task_id,
        requirements=req.requirements,
        agent_type=req.agent_type,
        git_url=req.git_url,
        branch=req.branch,
        github_token=req.github_token,
        llm_config=req.llm_config.model_dump(),
        work_dir=str(work_dir),
    )

    success, error_msg = await run_coding_agent(agent_req, db_session_factory)

    if success:
        _state.status = "completed"
        _state.error_message = None
        logger.info("agent_completed", extra={"event": "agent_completed", "task_id": req.task_id})
    else:
        _state.status = "failed"
        _state.error_message = error_msg
        logger.error(
            "agent_failed",
            extra={"event": "agent_failed", "task_id": req.task_id, "error": error_msg},
        )
