"""Agent invocation for the worker.

Accepts a WorkRequest dataclass (no DB session dependency).
Persists execution state to the worker's own worker_executions table.
Returns (success, error_message) tuple.
"""
import asyncio
import logging
import re
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from worker.git_utils import clone_repository

logger = logging.getLogger(__name__)

# Module-level import; set to None on ImportError so tests can still patch.
try:
    from simple_langchain_deepagent import DeepAgent, DeepAgentConfig
except ImportError:  # pragma: no cover
    DeepAgent = None  # type: ignore[assignment, misc]
    DeepAgentConfig = None  # type: ignore[assignment, misc]


@dataclass
class WorkRequest:
    task_id: str
    requirements: str
    agent_type: str
    work_dir: str
    git_url: str | None = None
    branch: str | None = None
    github_token: str | None = None
    llm_config: dict | None = None


def _resolve_agent_classes():
    """Return (DeepAgent, DeepAgentConfig), retrying import if needed."""
    global DeepAgent, DeepAgentConfig  # noqa: PLW0603
    if DeepAgent is not None and DeepAgentConfig is not None:
        return DeepAgent, DeepAgentConfig
    from simple_langchain_deepagent import DeepAgent as _DA, DeepAgentConfig as _DAC
    DeepAgent = _DA  # type: ignore[assignment]
    DeepAgentConfig = _DAC  # type: ignore[assignment]
    return DeepAgent, DeepAgentConfig


async def _persist_execution_start(
    task_id: str, agent_type: str, work_dir: str, session_factory
) -> None:
    """Upsert WorkExecution record at task start (handles retried tasks)."""
    if session_factory is None:
        return
    from sqlalchemy import select, update
    from worker.models import WorkExecution
    try:
        async with session_factory() as db:
            existing = await db.execute(
                select(WorkExecution).where(WorkExecution.task_id == uuid.UUID(task_id))
            )
            row = existing.scalar_one_or_none()
            if row:
                await db.execute(
                    update(WorkExecution)
                    .where(WorkExecution.task_id == uuid.UUID(task_id))
                    .values(
                        status="in_progress",
                        started_at=datetime.now(timezone.utc),
                        completed_at=None,
                        error_message=None,
                        work_dir_path=work_dir,
                    )
                )
            else:
                db.add(WorkExecution(
                    task_id=uuid.UUID(task_id),
                    agent_type=agent_type,
                    status="in_progress",
                    work_dir_path=work_dir,
                ))
            await db.commit()
    except Exception as exc:
        logger.warning("execution_persist_failed", extra={"error": str(exc)})


async def _persist_execution_end(
    task_id: str, status: str, error_message: str | None, session_factory
) -> None:
    """Update WorkExecution record at task completion."""
    if session_factory is None:
        return
    from worker.models import WorkExecution
    from sqlalchemy import update
    try:
        async with session_factory() as db:
            await db.execute(
                update(WorkExecution)
                .where(WorkExecution.task_id == uuid.UUID(task_id))
                .values(
                    status=status,
                    completed_at=datetime.now(timezone.utc),
                    error_message=error_message,
                )
            )
            await db.commit()
    except Exception as exc:
        logger.warning("execution_update_failed", extra={"error": str(exc)})


async def run_coding_agent(
    req: WorkRequest,
    db_session_factory=None,
) -> tuple[bool, str | None]:
    """Run the deep agent for the given WorkRequest.

    1. Persists WorkExecution record to worker's own DB.
    2. Clones the repository if git_url is set.
    3. Invokes DeepAgent.
    4. Updates WorkExecution on completion.
    5. Returns (True, None) on success, (False, error_message) on failure.
    """
    work_dir = Path(req.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    await _persist_execution_start(
        req.task_id, req.agent_type, str(work_dir), db_session_factory
    )

    # Clone repository if git_url is configured
    github_token = req.github_token or ""
    if req.git_url:
        safe_url = re.sub(r"https://[^@]+@", "https://", req.git_url)
        logger.info(
            "clone_started",
            extra={
                "event": "clone_started",
                "task_id": req.task_id,
                "git_url": safe_url,
                "branch": req.branch,
                "token_set": bool(github_token),
            },
        )
        try:
            await asyncio.to_thread(
                clone_repository,
                req.git_url,
                work_dir,
                branch=req.branch,
                github_token=github_token,
            )
            logger.info(
                "clone_succeeded",
                extra={"event": "clone_succeeded", "task_id": req.task_id, "branch": req.branch},
            )
        except Exception as exc:
            logger.error(
                "clone_failed",
                extra={"event": "clone_failed", "task_id": req.task_id, "error": str(exc)},
            )
            await _persist_execution_end(req.task_id, "failed", f"clone failed: {exc}", db_session_factory)
            return False, f"clone failed: {exc}"

    llm = req.llm_config or {}
    project_name = req.task_id[:8]

    logger.info(
        "agent_starting",
        extra={
            "event": "agent_starting",
            "task_id": req.task_id,
            "work_dir": str(work_dir),
            "llm_provider": llm.get("provider", "ollama"),
            "llm_model": llm.get("model", "qwen2.5-coder:7b"),
        },
    )

    try:
        AgentCls, ConfigCls = _resolve_agent_classes()
    except ImportError:
        tb = traceback.format_exc()
        logger.error("agent_import_failed", extra={"event": "agent_import_failed", "traceback": tb})
        error_msg = f"Failed to import simple_langchain_deepagent: {tb}"
        await _persist_execution_end(req.task_id, "failed", error_msg, db_session_factory)
        return False, error_msg

    try:
        config = ConfigCls(
            working_directory=work_dir,
            project_name=project_name,
            requirement=req.requirements,
            llm_provider=llm.get("provider") or "ollama",
            llm_model=llm.get("model") or "qwen2.5-coder:7b",
            llm_temperature=float(llm.get("temperature") or 0.2),
            ollama_base_url=llm.get("ollama_base_url") or "http://localhost:11434",
            openai_api_key=llm.get("openai_api_key") or "",
            anthropic_api_key=llm.get("anthropic_api_key") or "",
        )
        # Run in a thread so the event loop (and heartbeat task) stays responsive
        # during the potentially long-running synchronous agent execution.
        agent_instance = AgentCls(config)
        result = await asyncio.to_thread(agent_instance.run)
        # DeepAgentResult has no .error field; exceptions are caught below
        summary = getattr(result, "summary", None)

        logger.info("agent_succeeded", extra={"event": "agent_succeeded", "task_id": req.task_id})
        await _persist_execution_end(req.task_id, "completed", None, db_session_factory)
        return True, None

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(
            "agent_exception",
            extra={"event": "agent_exception", "task_id": req.task_id, "error": str(exc)},
        )
        await _persist_execution_end(req.task_id, "failed", str(exc), db_session_factory)
        return False, str(exc)
