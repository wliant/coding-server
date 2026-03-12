"""Worker FastAPI application."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from worker.config import settings
from worker.registration import register_with_controller, start_heartbeat_loop
from worker.routes import get_current_state, make_router, _set_state_free, _state


def _configure_logging() -> None:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


_configure_logging()
logger = logging.getLogger(__name__)


def _get_worker_url() -> str:
    """Determine this worker's externally-reachable URL.

    In Docker Compose the container hostname is the service name.
    WORKER_URL env var can override for non-standard deployments.
    """
    import os
    import socket

    override = os.environ.get("WORKER_URL")
    if override:
        return override
    hostname = socket.gethostname()
    return f"http://{hostname}:{settings.WORKER_PORT}"


def _run_migrations() -> None:
    """Run worker DB migrations synchronously."""
    from alembic.config import Config
    from alembic import command

    # Locate alembic.ini relative to this package's installed location
    alembic_ini = Path(__file__).parent.parent.parent / "alembic" / "alembic.ini"
    if not alembic_ini.exists():
        # Fallback: look relative to CWD (dev/docker layout)
        alembic_ini = Path("/app/alembic/alembic.ini")

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    command.upgrade(cfg, "head")
    logger.info("worker_migrations_applied", extra={"event": "worker_migrations_applied"})


async def _restore_state_from_db(session_factory) -> None:
    """Restore _state from the most recent WorkExecution on restart.

    - in_progress: mark as failed in DB (worker crashed mid-task), restore failed state
    - completed/failed: restore state so /push and /status work after restart,
      but only if the job hasn't already been cleaned up
    - no record: leave state as free
    """
    from datetime import datetime, timezone

    from sqlalchemy import select, text, update
    from worker.models import WorkExecution

    try:
        async with session_factory() as db:
            result = await db.execute(
                select(WorkExecution)
                .order_by(WorkExecution.started_at.desc())
                .limit(1)
            )
            execution = result.scalar_one_or_none()
            if execution is None:
                return

            if execution.status == "in_progress":
                # Worker crashed while task was running — mark as failed in DB
                now = datetime.now(timezone.utc)
                await db.execute(
                    update(WorkExecution)
                    .where(WorkExecution.id == execution.id)
                    .values(
                        status="failed",
                        error_message="Worker restarted while task was in progress",
                        completed_at=now,
                    )
                )
                await db.commit()

                # Check if the reaper already reset the job to pending
                job_row = await db.execute(
                    text("SELECT status FROM jobs WHERE id = :task_id"),
                    {"task_id": execution.task_id},
                )
                job_status = (job_row.fetchone() or (None,))[0]

                if job_status == "in_progress":
                    # Reaper hasn't run yet — restore failed state so heartbeat updates job
                    _state.status = "failed"
                    _state.task_id = str(execution.task_id)
                    _state.work_dir_path = execution.work_dir_path
                    _state.error_message = "Worker restarted while task was in progress"
                    logger.info(
                        "state_restored_as_failed",
                        extra={
                            "event": "state_restored_as_failed",
                            "task_id": str(execution.task_id),
                            "work_dir_path": execution.work_dir_path,
                        },
                    )
                else:
                    # Reaper already reset job to pending (or job is gone) — stay free
                    logger.info(
                        "state_restore_skipped_job_already_reset",
                        extra={
                            "event": "state_restore_skipped_job_already_reset",
                            "job_status": job_status,
                            "task_id": str(execution.task_id),
                        },
                    )
            else:
                # completed or failed — only restore if the job hasn't been cleaned yet
                job_row = await db.execute(
                    text("SELECT status FROM jobs WHERE id = :task_id"),
                    {"task_id": execution.task_id},
                )
                job_status = (job_row.fetchone() or (None,))[0]
                if job_status in ("cleaned", "cleaning_up", None):
                    logger.info(
                        "state_restore_skipped",
                        extra={
                            "event": "state_restore_skipped",
                            "task_id": str(execution.task_id),
                            "job_status": job_status,
                        },
                    )
                    return

                _state.status = execution.status
                _state.task_id = str(execution.task_id)
                _state.work_dir_path = execution.work_dir_path
                if execution.status == "failed":
                    _state.error_message = execution.error_message
                logger.info(
                    "state_restored",
                    extra={
                        "event": "state_restored",
                        "task_id": str(execution.task_id),
                        "work_dir_path": execution.work_dir_path,
                        "status": execution.status,
                    },
                )
    except Exception as exc:
        logger.warning("state_restore_failed", extra={"error": str(exc)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    import socket

    # Run worker DB migrations before accepting connections
    await asyncio.to_thread(_run_migrations)

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Restore last task state so /push and /status work after a restart
    await _restore_state_from_db(session_factory)

    worker_url = _get_worker_url()

    # Stable identity: use configured WORKER_ID or fall back to hostname
    stable_worker_id = settings.WORKER_ID or socket.gethostname()

    worker_id = await register_with_controller(
        worker_id=stable_worker_id,
        controller_url=settings.CONTROLLER_URL,
        agent_type=settings.AGENT_TYPE,
        worker_url=worker_url,
    )

    # Store worker_id in app state for access in routes
    app.state.worker_id = worker_id

    heartbeat_task = asyncio.create_task(
        start_heartbeat_loop(
            worker_id=stable_worker_id,
            controller_url=settings.CONTROLLER_URL,
            get_status=get_current_state,
            agent_type=settings.AGENT_TYPE,
            worker_url=worker_url,
            interval_seconds=settings.HEARTBEAT_INTERVAL_SECONDS,
            on_should_free=_set_state_free,
        )
    )

    logger.info(
        "worker_started",
        extra={
            "event": "worker_started",
            "worker_id": worker_id,
            "agent_type": settings.AGENT_TYPE,
            "work_dir": settings.WORK_DIR,
        },
    )

    yield

    heartbeat_task.cancel()
    await engine.dispose()
    logger.info("worker_stopped", extra={"event": "worker_stopped", "worker_id": worker_id})


def create_app() -> FastAPI:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    app = FastAPI(title="OpenHands Agent Worker", version="1.0.0", lifespan=lifespan)

    cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    router = make_router(work_dir_base=settings.WORK_DIR, db_session_factory=session_factory)
    app.include_router(router)
    return app


app = create_app()
