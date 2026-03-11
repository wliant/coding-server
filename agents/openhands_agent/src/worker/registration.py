"""Worker registration and heartbeat loop."""
import asyncio
import logging
from typing import Callable

import httpx

logger = logging.getLogger(__name__)


async def register_with_controller(
    worker_id: str,
    controller_url: str,
    agent_type: str,
    worker_url: str,
    retry_interval: float = 5.0,
) -> str:
    """Register this worker with the Controller. Retries until successful.

    Proposes `worker_id` to the controller; the controller accepts it unchanged.
    Returns the confirmed worker_id.
    """
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{controller_url}/workers/register",
                    json={
                        "worker_id": worker_id,
                        "agent_type": agent_type,
                        "worker_url": worker_url,
                    },
                )
                resp.raise_for_status()
                confirmed_id = resp.json()["worker_id"]
                logger.info(
                    "registration_success",
                    extra={
                        "event": "registration_success",
                        "worker_id": confirmed_id,
                        "agent_type": agent_type,
                    },
                )
                return confirmed_id
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
    on_should_free: Callable[[], None] | None = None,
) -> None:
    """Periodically send heartbeats to the Controller.

    If the controller returns 404 (e.g. after a restart), automatically
    re-registers and continues with the new worker_id.

    If the controller responds with should_free=True (job was already reset by
    the reaper), calls on_should_free() to clear local state.

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
                    # Controller restarted — re-register with the same stable worker_id
                    logger.warning(
                        "heartbeat_worker_not_found_re_registering",
                        extra={
                            "event": "heartbeat_worker_not_found_re_registering",
                            "worker_id": current_worker_id,
                        },
                    )
                    current_worker_id = await register_with_controller(
                        worker_id=worker_id,
                        controller_url=controller_url,
                        agent_type=agent_type,
                        worker_url=worker_url,
                    )
                else:
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("should_free") and on_should_free:
                        logger.info(
                            "heartbeat_should_free",
                            extra={
                                "event": "heartbeat_should_free",
                                "worker_id": current_worker_id,
                                "task_id": current.get("task_id"),
                            },
                        )
                        on_should_free()
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
