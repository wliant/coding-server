import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text
from api.db import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    components: dict[str, str]


async def _check_database() -> str:
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        logger.exception("Database health check failed")
        return "unavailable"


async def _check_redis(request: Request) -> str:
    try:
        await request.app.state.redis.ping()
        return "ok"
    except Exception:
        logger.exception("Redis health check failed")
        return "unavailable"


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Health check — always returns HTTP 200 to keep Docker healthcheck stable."""
    db_status = await _check_database()
    redis_status = await _check_redis(request)

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        components={
            "database": db_status,
            "redis": redis_status,
        },
    )
