"""API route to proxy sandbox status from the Controller."""
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException

from api.schemas.sandbox import SandboxStatus

router = APIRouter(prefix="/sandboxes", tags=["sandboxes"])

CONTROLLER_URL = os.getenv("CONTROLLER_URL", "http://controller:8003")

logger = logging.getLogger(__name__)


@router.get("", response_model=list[SandboxStatus])
async def list_sandboxes():
    """Proxy GET /sandboxes to the Controller service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{CONTROLLER_URL}/sandboxes")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("controller_error", extra={"status": exc.response.status_code})
        raise HTTPException(status_code=502, detail="Controller returned an error") from exc
    except Exception as exc:
        logger.warning("controller_unreachable", extra={"error": str(exc)})
        raise HTTPException(status_code=503, detail="Controller service is unavailable") from exc
