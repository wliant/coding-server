"""Controller FastAPI application."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pythonjsonlogger import jsonlogger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from controller.config import settings
from controller.delegator import delegator_loop, process_task_completion
from controller.registry import WorkerRegistry
from controller.routes import make_router


def _configure_logging() -> None:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def create_app(
    registry: WorkerRegistry | None = None,
    on_completion_callback=None,
) -> FastAPI:
    """Factory function — allows test injection of a custom registry and callback."""
    if registry is None:
        registry = WorkerRegistry()

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    if on_completion_callback is None:
        async def on_completion_callback(
            worker_id: str, task_id: str, status: str, error_message: str | None
        ) -> bool:
            async with session_factory() as db:
                return await process_task_completion(db, registry, worker_id, task_id, status, error_message)
            # Do NOT set_free here — worker stays in completed/failed state until user triggers
            # "Clean Up", at which point the controller calls /free on the worker.

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _configure_logging()
        task = asyncio.create_task(delegator_loop(registry, session_factory, settings))
        logging.getLogger(__name__).info(
            "controller_started", extra={"event": "controller_started"}
        )
        yield
        task.cancel()
        await engine.dispose()
        logging.getLogger(__name__).info(
            "controller_stopped", extra={"event": "controller_stopped"}
        )

    app = FastAPI(title="Agent Controller", version="1.0.0", lifespan=lifespan)
    router = make_router(registry=registry, on_completion_callback=on_completion_callback)
    app.include_router(router)
    return app


app = create_app()
