import logging
import logging.config
import os
import time
import uuid
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pythonjsonlogger import jsonlogger
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from api.db import engine
from api.routes.agents import router as agents_router
from api.routes.health import router as health_router
from api.routes.projects import router as projects_router
from api.routes.settings import router as settings_router
from api.routes.tasks import router as tasks_router
from api.routes.workers import router as workers_router
from api.routes.sandboxes import router as sandboxes_router

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    app.state.redis = aioredis.Redis.from_url(REDIS_URL, decode_responses=True)
    logger.info("API startup complete", extra={"event": "startup"})
    yield
    await app.state.redis.aclose()
    await engine.dispose()
    logger.info("API shutdown complete", extra={"event": "shutdown"})


app = FastAPI(
    title="Multi-Agent Software Development System API",
    version="0.1.0",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.error("database integrity error", extra={"error": str(exc.orig)})
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc.orig).split("\n")[0]},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("database error", extra={"error": str(exc)})
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred. Please try again."},
    )


app.include_router(health_router)
app.include_router(agents_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(settings_router)
app.include_router(workers_router)
app.include_router(sandboxes_router)
