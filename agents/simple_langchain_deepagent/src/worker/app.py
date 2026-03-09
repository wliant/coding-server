"""Worker FastAPI application."""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from pythonjsonlogger import jsonlogger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from worker.config import settings
from worker.registration import register_with_controller, start_heartbeat_loop
from worker.routes import get_current_state, make_router, _state


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
    """Restore _state from an in-progress WorkExecution on restart.

    Only restores in_progress tasks (agent was running when container crashed).
    Completed tasks are NOT restored: restoring completed state blocks the worker
    from accepting new tasks until the old task is manually cleaned up, creating
    a stuck-worker deadlock.
    """
    from sqlalchemy import select
    from worker.models import WorkExecution

    try:
        async with session_factory() as db:
            result = await db.execute(
                select(WorkExecution)
                .where(WorkExecution.status == "in_progress")
                .order_by(WorkExecution.started_at.desc())
                .limit(1)
            )
            execution = result.scalar_one_or_none()
            if execution:
                _state.status = "in_progress"
                _state.task_id = str(execution.task_id)
                _state.work_dir_path = execution.work_dir_path
                logger.info(
                    "state_restored",
                    extra={
                        "event": "state_restored",
                        "task_id": str(execution.task_id),
                        "work_dir_path": execution.work_dir_path,
                        "status": "in_progress",
                    },
                )
    except Exception as exc:
        logger.warning("state_restore_failed", extra={"error": str(exc)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run worker DB migrations before accepting connections
    await asyncio.to_thread(_run_migrations)

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Restore last-completed-task state so push requests work after a restart
    await _restore_state_from_db(session_factory)

    worker_url = _get_worker_url()

    worker_id = await register_with_controller(
        controller_url=settings.CONTROLLER_URL,
        agent_type=settings.AGENT_TYPE,
        worker_url=worker_url,
    )

    # Store worker_id in app state for access in routes
    app.state.worker_id = worker_id

    heartbeat_task = asyncio.create_task(
        start_heartbeat_loop(
            controller_url=settings.CONTROLLER_URL,
            worker_id=worker_id,
            get_status=get_current_state,
            agent_type=settings.AGENT_TYPE,
            worker_url=worker_url,
            interval_seconds=settings.HEARTBEAT_INTERVAL_SECONDS,
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

    app = FastAPI(title="Deep Agent Worker", version="1.0.0", lifespan=lifespan)
    router = make_router(work_dir_base=settings.WORK_DIR, db_session_factory=session_factory)
    app.include_router(router)
    return app


app = create_app()
