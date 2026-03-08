"""Worker registration and heartbeat loop."""
import asyncio
import logging
from typing import Callable

import httpx

logger = logging.getLogger(__name__)


async def register_with_controller(
    controller_url: str,
    agent_type: str,
    worker_url: str,
    retry_interval: float = 5.0,
) -> str:
    """Register this worker with the Controller. Retries until successful.

    Returns the worker_id assigned by the Controller.
    """
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{controller_url}/workers/register",
                    json={"agent_type": agent_type, "worker_url": worker_url},
                )
                resp.raise_for_status()
                worker_id = resp.json()["worker_id"]
                logger.info(
                    "registration_success",
                    extra={
                        "event": "registration_success",
                        "worker_id": worker_id,
                        "agent_type": agent_type,
                    },
                )
                return worker_id
        except Exception as exc:
            logger.warning(
                "registration_retry",
                extra={
                    "event": "registration_retry",
                    "error": str(exc),
                    "retry_in": retry_interval,
                },
            )
            await asyncio.sleep(retry_interval)


async def start_heartbeat_loop(
    controller_url: str,
    worker_id: str,
    get_status: Callable[[], dict],
    agent_type: str,
    worker_url: str,
    interval_seconds: int = 15,
) -> None:
    """Periodically send heartbeats to the Controller.

    If the controller returns 404 (e.g. after a restart), automatically
    re-registers and continues with the new worker_id.

    `get_status` is a callable returning dict with keys:
      - status: str (free|in_progress|completed|failed)
      - task_id: str | None
      - error_message: str | None
    """
    current_worker_id = worker_id
    while True:
        await asyncio.sleep(interval_seconds)
        current = get_status()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{controller_url}/workers/{current_worker_id}/heartbeat",
                    json={
                        "status": current["status"],
                        "task_id": current.get("task_id"),
                        "error_message": current.get("error_message"),
                    },
                )
                if resp.status_code == 404:
                    # Controller restarted — re-register to get a new worker_id
                    logger.warning(
                        "heartbeat_worker_not_found_re_registering",
                        extra={
                            "event": "heartbeat_worker_not_found_re_registering",
                            "old_worker_id": current_worker_id,
                        },
                    )
                    current_worker_id = await register_with_controller(
                        controller_url=controller_url,
                        agent_type=agent_type,
                        worker_url=worker_url,
                    )
                else:
                    logger.debug(
                        "heartbeat_sent",
                        extra={
                            "event": "heartbeat_sent",
                            "worker_id": current_worker_id,
                            "status": current["status"],
                        },
                    )
        except Exception as exc:
            logger.warning(
                "heartbeat_failed",
                extra={"event": "heartbeat_failed", "error": str(exc)},
            )
