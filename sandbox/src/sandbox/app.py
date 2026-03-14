"""Sandbox FastAPI application."""
import asyncio
import logging
import os
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger

from sandbox.config import settings
from sandbox.mcp_server import create_mcp_server
from sandbox.registration import register_with_controller, start_heartbeat_loop
from sandbox.routes import make_router


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


def _get_sandbox_url() -> str:
    override = os.environ.get("SANDBOX_URL")
    if override:
        return override
    hostname = socket.gethostname()
    return f"http://{hostname}:{settings.SANDBOX_PORT}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    sandbox_url = _get_sandbox_url()
    stable_sandbox_id = settings.SANDBOX_ID or socket.gethostname()

    sandbox_id = await register_with_controller(
        sandbox_id=stable_sandbox_id,
        controller_url=settings.CONTROLLER_URL,
        sandbox_url=sandbox_url,
        labels=settings.labels_list,
    )

    app.state.sandbox_id = sandbox_id

    heartbeat_task = asyncio.create_task(
        start_heartbeat_loop(
            controller_url=settings.CONTROLLER_URL,
            sandbox_id=stable_sandbox_id,
            sandbox_url=sandbox_url,
            labels=settings.labels_list,
            interval_seconds=settings.HEARTBEAT_INTERVAL_SECONDS,
        )
    )

    logger.info(
        "sandbox_started",
        extra={
            "event": "sandbox_started",
            "sandbox_id": sandbox_id,
            "labels": settings.labels_list,
            "workspace_dir": settings.WORKSPACE_DIR,
        },
    )

    yield

    heartbeat_task.cancel()
    logger.info("sandbox_stopped", extra={"event": "sandbox_stopped", "sandbox_id": sandbox_id})


def create_app() -> FastAPI:
    app = FastAPI(title="Sandbox", version="1.0.0", lifespan=lifespan)

    cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    router = make_router(workspace_dir=settings.WORKSPACE_DIR, labels=settings.labels_list)
    app.include_router(router)

    # Mount MCP SSE endpoint
    mcp = create_mcp_server(
        workspace_dir=settings.WORKSPACE_DIR,
        labels=settings.labels_list,
    )
    app.mount("/mcp", mcp.http_app())

    return app


app = create_app()
