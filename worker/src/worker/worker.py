import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from pythonjsonlogger import jsonlogger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from worker.agent_runner import run_coding_agent
from worker.config import settings
from worker.lease_manager import acquire_lease, get_next_pending_job, reap_expired_leases, release_lease
from worker.models import Base, Job, Project


def _configure_logging() -> None:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


logger = logging.getLogger(__name__)


async def _lease_renewal_loop(
    session_factory: async_sessionmaker,
    job_id: uuid.UUID,
    worker_id: str,
    renewal_interval: int,
    ttl: int,
) -> None:
    """Background task: renew the lease every renewal_interval seconds."""
    from worker.lease_manager import renew_lease

    while True:
        await asyncio.sleep(renewal_interval)
        async with session_factory() as db:
            await renew_lease(db, job_id, worker_id, ttl)


async def _run_one_poll_cycle(
    db: AsyncSession,
    worker_id: str,
    cfg,
) -> bool:
    """Execute one poll cycle: reap stale leases, claim a pending job, run agent.

    Returns True if a job was processed, False if no jobs were available.
    """
    # Reap any stale leases from crashed workers
    await reap_expired_leases(db)

    # Find the next pending job
    job = await get_next_pending_job(db)
    if job is None:
        return False

    # Attempt to claim the lease atomically
    claimed = await acquire_lease(db, job.id, worker_id, cfg.LEASE_TTL_SECONDS)
    if not claimed:
        # Another worker claimed it first
        return False

    # Refresh job to get updated state
    await db.refresh(job)

    # Load the associated project
    result = await db.execute(select(Project).where(Project.id == job.project_id))
    project = result.scalar_one()

    # Run the agent
    success, error_msg = await run_coding_agent(db, job, project, cfg)

    # Update final job state
    now = datetime.now(timezone.utc)
    if success:
        job.status = "completed"
        job.completed_at = now
        job.updated_at = now
        logger.info(
            "task_completed",
            extra={"event": "task_completed", "job_id": str(job.id)},
        )
    else:
        job.status = "failed"
        job.completed_at = now
        job.error_message = error_msg
        job.updated_at = now
        logger.warning(
            "task_failed",
            extra={"event": "task_failed", "job_id": str(job.id), "error": error_msg},
        )

    await db.commit()
    await release_lease(db, job.id)
    return True


async def main_loop() -> None:
    """Main worker polling loop.

    Polls the database for pending jobs, claims them via lease, executes the
    coding agent, and transitions jobs to Completed or Failed.
    """
    worker_id = str(uuid.uuid4())
    logger.info("worker_ready", extra={"event": "worker_ready", "worker_id": worker_id})

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    while True:
        try:
            async with session_factory() as db:
                await _run_one_poll_cycle(db, worker_id, settings)
        except Exception as exc:
            logger.error(
                "poll_cycle_error",
                extra={"event": "poll_cycle_error", "error": str(exc)},
            )

        await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    task = asyncio.create_task(main_loop())
    logger.info("Worker startup complete", extra={"event": "startup"})
    yield
    task.cancel()
    logger.info("Worker shutdown complete", extra={"event": "shutdown"})


app = FastAPI(title="Worker", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}
