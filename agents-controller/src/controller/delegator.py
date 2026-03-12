"""Controller polling loop: reap → renew leases → handle cleanup → delegate tasks."""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from controller.config import settings
from controller.models import Agent, Job, Project
from controller.registry import WorkerRegistry

logger = logging.getLogger(__name__)


async def _reap_unreachable_workers(
    registry: WorkerRegistry, db: AsyncSession, timeout_seconds: int
) -> None:
    """Mark stale workers as unreachable and release their task leases."""
    stale = await registry.get_stale_workers(timeout_seconds)
    for rec in stale:
        logger.warning(
            "worker_unreachable",
            extra={
                "event": "worker_unreachable",
                "worker_id": rec.worker_id,
                "last_heartbeat_ago": (
                    datetime.now(timezone.utc) - rec.last_heartbeat_at
                ).total_seconds(),
            },
        )
        await registry.mark_unreachable(rec.worker_id)

        if rec.current_task_id:
            # Release task lease — return task to pending
            await db.execute(
                update(Job)
                .where(
                    Job.id == uuid.UUID(rec.current_task_id),
                    Job.status == "in_progress",
                )
                .values(
                    status="pending",
                    lease_holder=None,
                    lease_expires_at=None,
                    assigned_worker_id=None,
                    assigned_worker_url=None,
                    updated_at=datetime.now(timezone.utc),
                )
            )
    if stale:
        await db.commit()


async def _renew_active_leases(
    registry: WorkerRegistry, db: AsyncSession, lease_ttl_seconds: int
) -> None:
    """Extend lease expiry for workers that are still alive."""
    workers = await registry.get_all()
    now = datetime.now(timezone.utc)
    renewed = 0
    for rec in workers:
        if rec.status == "in_progress" and rec.current_task_id:
            await db.execute(
                update(Job)
                .where(
                    Job.id == uuid.UUID(rec.current_task_id),
                    Job.lease_holder == rec.worker_id,
                )
                .values(
                    lease_expires_at=datetime.fromtimestamp(
                        now.timestamp() + lease_ttl_seconds, tz=timezone.utc
                    ),
                    updated_at=now,
                )
            )
            renewed += 1
    if renewed:
        await db.commit()


async def _handle_cleaning_up_tasks(
    registry: WorkerRegistry, db: AsyncSession
) -> None:
    """Call /free on worker for tasks in cleaning_up state."""
    result = await db.execute(
        select(Job).where(
            Job.status == "cleaning_up",
            Job.assigned_worker_url.isnot(None),
        )
    )
    cleaning_jobs = result.scalars().all()

    for job in cleaning_jobs:
        worker_id_to_free = job.assigned_worker_id
        now = datetime.now(timezone.utc)
        worker_gone = False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{job.assigned_worker_url}/free")
                resp.raise_for_status()
        except httpx.ConnectError:
            # Worker container is gone (restarted/replaced) — treat as already freed
            worker_gone = True
            logger.warning(
                "cleanup_worker_unreachable",
                extra={
                    "event": "cleanup_worker_unreachable",
                    "task_id": str(job.id),
                    "worker_url": job.assigned_worker_url,
                },
            )
        except Exception as exc:
            logger.error(
                "cleanup_failed",
                extra={"event": "cleanup_failed", "task_id": str(job.id), "error": str(exc)},
            )
            continue

        # Mark job as cleaned (whether worker responded or was already gone)
        await db.execute(
            update(Job)
            .where(Job.id == job.id)
            .values(
                status="cleaned",
                assigned_worker_id=None,
                assigned_worker_url=None,
                updated_at=now,
            )
        )
        if worker_id_to_free and not worker_gone:
            await registry.set_free(worker_id_to_free)
        logger.info(
            "cleanup_succeeded",
            extra={"event": "cleanup_succeeded", "task_id": str(job.id), "worker_gone": worker_gone},
        )

    if cleaning_jobs:
        await db.commit()


async def _delegate_pending_tasks(
    registry: WorkerRegistry, db: AsyncSession, lease_ttl_seconds: int
) -> None:
    """Find pending tasks and delegate to free matching workers."""
    # Fetch pending jobs joined with agent for agent type
    result = await db.execute(
        select(Job, Project, Agent)
        .join(Project, Job.project_id == Project.id)
        .outerjoin(Agent, Job.agent_id == Agent.id)
        .where(Job.status == "pending")
        .order_by(Job.created_at.asc())
        .limit(10)
    )
    pending_rows = result.all()

    for job, project, agent in pending_rows:
        agent_type = agent.identifier if agent else None
        if not agent_type:
            continue

        worker = await registry.get_free_worker_for_agent_type(agent_type)
        if worker is None:
            continue

        # Atomically claim the task
        now = datetime.now(timezone.utc)
        expires_at = datetime.fromtimestamp(now.timestamp() + lease_ttl_seconds, tz=timezone.utc)
        result2 = await db.execute(
            update(Job)
            .where(Job.id == job.id, Job.status == "pending")
            .values(
                status="in_progress",
                lease_holder=worker.worker_id,
                lease_expires_at=expires_at,
                assigned_worker_id=worker.worker_id,
                assigned_worker_url=worker.worker_url,
                started_at=now,
                updated_at=now,
            )
            .returning(Job.id)
        )
        claimed = result2.fetchone()
        if claimed is None:
            # Race — another controller (or test) claimed it
            continue

        await db.commit()

        # Fetch LLM config from main API
        llm_config = await _fetch_llm_config()

        # Build work payload
        github_token = llm_config.pop("github_token", None)
        work_payload = {
            "task_id": str(job.id),
            "requirements": job.requirement,
            "agent_type": agent_type,
            "git_url": project.git_url,
            "branch": job.branch,
            "github_token": github_token,
            "llm_config": llm_config,
            "task_type": job.task_type,
            "commits_to_review": job.commits_to_review,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{worker.worker_url}/work", json=work_payload)
                resp.raise_for_status()

            await registry.assign_task(worker.worker_id, str(job.id))
            logger.info(
                "task_delegated",
                extra={
                    "event": "task_delegated",
                    "task_id": str(job.id),
                    "worker_id": worker.worker_id,
                    "agent_type": agent_type,
                },
            )
        except Exception as exc:
            # Rollback claim
            logger.error(
                "delegation_failed",
                extra={
                    "event": "delegation_failed",
                    "task_id": str(job.id),
                    "worker_id": worker.worker_id,
                    "error": str(exc),
                },
            )
            await db.execute(
                update(Job)
                .where(Job.id == job.id)
                .values(
                    status="pending",
                    lease_holder=None,
                    lease_expires_at=None,
                    assigned_worker_id=None,
                    assigned_worker_url=None,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()


async def _fetch_llm_config() -> dict:
    """Fetch LLM and GitHub config from main API settings."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.API_URL}/settings")
            resp.raise_for_status()
            data = resp.json()
            s = data.get("settings", {})
            return {
                "provider": s.get("agent.simple_crewai.llm_provider", "ollama"),
                "model": s.get("agent.simple_crewai.llm_model", "qwen2.5-coder:7b"),
                "temperature": float(s.get("agent.simple_crewai.llm_temperature", "0.2")),
                "ollama_base_url": s.get("agent.simple_crewai.ollama_base_url", "http://localhost:11434"),
                "openai_api_key": s.get("agent.simple_crewai.openai_api_key") or None,
                "anthropic_api_key": s.get("agent.simple_crewai.anthropic_api_key") or None,
                "github_token": s.get("github.token") or None,
            }
    except Exception as exc:
        logger.warning("settings_fetch_failed", extra={"error": str(exc)})
        return {"provider": "ollama", "model": "qwen2.5-coder:7b", "temperature": 0.2}


async def process_task_completion(
    db: AsyncSession,
    registry: WorkerRegistry,
    worker_id: str,
    task_id: str,
    status: str,
    error_message: str | None,
) -> bool:
    """Update job in DB when worker reports completion via heartbeat.

    Also restores assigned_worker_url/id in case they were cleared by a
    transient reap cycle while the agent was running.

    Returns True if the job was updated, False if the job was not in_progress
    (e.g. the reaper already reset it to pending).
    """
    now = datetime.now(timezone.utc)
    worker_rec = await registry.get(worker_id)
    worker_url = worker_rec.worker_url if worker_rec else None
    result = await db.execute(
        update(Job)
        .where(
            Job.id == uuid.UUID(task_id),
            Job.status == "in_progress",  # Never overwrite cleaning_up/cleaned/pending
        )
        .values(
            status=status,
            completed_at=now,
            error_message=error_message,
            assigned_worker_id=worker_id,
            assigned_worker_url=worker_url,
            updated_at=now,
        )
        .returning(Job.id)
    )
    updated = result.fetchone()
    await db.commit()
    if updated:
        logger.info(
            "task_completed" if status == "completed" else "task_failed",
            extra={"event": f"task_{status}", "task_id": task_id, "worker_id": worker_id},
        )
    else:
        logger.info(
            "task_completion_ignored",
            extra={
                "event": "task_completion_ignored",
                "task_id": task_id,
                "worker_id": worker_id,
                "status": status,
            },
        )
    return updated is not None


async def run_poll_cycle(
    registry: WorkerRegistry,
    session_factory: async_sessionmaker,
    cfg,
) -> None:
    """Execute one complete poll cycle."""
    async with session_factory() as db:
        await _reap_unreachable_workers(registry, db, cfg.HEARTBEAT_TIMEOUT_SECONDS)
        await _renew_active_leases(registry, db, cfg.LEASE_TTL_SECONDS)
        await _handle_cleaning_up_tasks(registry, db)
        await _delegate_pending_tasks(registry, db, cfg.LEASE_TTL_SECONDS)


async def delegator_loop(
    registry: WorkerRegistry,
    session_factory: async_sessionmaker,
    cfg,
) -> None:
    """Main delegator polling loop."""
    logger.info("delegator_started", extra={"event": "delegator_started"})
    while True:
        try:
            await run_poll_cycle(registry, session_factory, cfg)
        except Exception as exc:
            logger.error(
                "poll_cycle_error",
                extra={"event": "poll_cycle_error", "error": str(exc)},
            )
        await asyncio.sleep(cfg.POLL_INTERVAL_SECONDS)
