import os
import asyncpg
import httpx
import pytest
from datetime import datetime, timezone
from pathlib import Path

BASE_URL     = os.environ.get("BASE_URL",    "http://localhost:3100")
API_URL      = os.environ.get("API_URL",     "http://localhost:8100")
WORKER_URL   = os.environ.get("WORKER_URL",  "http://localhost:8101")
DATABASE_URL = os.environ.get("DATABASE_URL",
                              "postgresql://postgres:postgres@localhost:5532/madm")

# ---- log directory ----

@pytest.fixture(scope="session")
def log_dir() -> Path:
    d = Path("logs") / datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    d.mkdir(parents=True, exist_ok=True)
    return d

@pytest.fixture(scope="session", autouse=True)
def capture_docker_logs(log_dir: Path):
    """Capture logs from all compose services into log_dir at session teardown.
    Skips silently if the Docker socket is not available."""
    import docker
    project = os.environ.get("COMPOSE_PROJECT", "madm_e2e")
    start_time = datetime.now(tz=timezone.utc)

    try:
        client = docker.from_env()
    except Exception:
        yield log_dir
        return

    yield log_dir

    try:
        containers = client.containers.list(
            all=True,
            filters={"label": f"com.docker.compose.project={project}"},
        )
        for container in containers:
            service = container.labels.get("com.docker.compose.service", container.name)
            log_path = log_dir / f"{service}.log"
            logs = container.logs(since=start_time, timestamps=True)
            log_path.write_bytes(logs)
    except Exception:
        pass

# ---- http client (sync — usable in both sync and async tests) ----

@pytest.fixture
def http():
    with httpx.Client(timeout=10.0) as client:
        yield client

# ---- db connection (function-scoped to avoid cross-loop issues) ----

@pytest.fixture
async def db():
    # asyncpg uses postgresql:// (strip +asyncpg if present)
    dsn = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    yield conn
    await conn.close()

# ---- playwright base_url override ----

@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL
