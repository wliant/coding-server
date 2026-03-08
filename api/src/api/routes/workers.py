"""API route to proxy worker status from the Controller."""
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException

from api.schemas.task import WorkerStatus

router = APIRouter(prefix="/workers", tags=["workers"])

CONTROLLER_URL = os.getenv("CONTROLLER_URL", "http://controller:8003")

logger = logging.getLogger(__name__)


@router.get("", response_model=list[WorkerStatus])
async def list_workers():
    """Proxy GET /workers to the Controller service.

    Returns 503 if the Controller is unreachable.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{CONTROLLER_URL}/workers")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("controller_error", extra={"status": exc.response.status_code})
        raise HTTPException(status_code=502, detail="Controller returned an error") from exc
    except Exception as exc:
        logger.warning("controller_unreachable", extra={"error": str(exc)})
        raise HTTPException(status_code=503, detail="Controller service is unavailable") from exc
