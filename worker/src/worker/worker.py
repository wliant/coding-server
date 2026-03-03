import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pythonjsonlogger import jsonlogger

from worker.config import settings


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


async def main_loop() -> None:
    """BLMOVE-based job consumer loop skeleton."""
    logger.info("worker ready", extra={"event": "worker_ready"})
    while True:
        await asyncio.sleep(1)


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
