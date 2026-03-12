"""Sandbox registration and heartbeat loop."""
import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


async def register_with_controller(
    sandbox_id: str,
    controller_url: str,
    sandbox_url: str,
    labels: list[str],
    retry_interval: float = 5.0,
) -> str:
    """Register this sandbox with the Controller. Retries until successful."""
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{controller_url}/sandboxes/register",
                    json={
                        "sandbox_id": sandbox_id,
                        "sandbox_url": sandbox_url,
                        "labels": labels,
                    },
                )
                resp.raise_for_status()
                confirmed_id = resp.json()["sandbox_id"]
                logger.info(
                    "registration_success",
                    extra={
                        "event": "registration_success",
                        "sandbox_id": confirmed_id,
                        "labels": labels,
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
    sandbox_id: str,
    sandbox_url: str,
    labels: list[str],
    interval_seconds: int = 15,
) -> None:
    """Periodically send heartbeats to the Controller.

    If the controller returns 404, automatically re-registers.
    """
    current_sandbox_id = sandbox_id
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{controller_url}/sandboxes/{current_sandbox_id}/heartbeat",
                    json={"status": "free"},
                )
                if resp.status_code == 404:
                    logger.warning(
                        "heartbeat_sandbox_not_found_re_registering",
                        extra={
                            "event": "heartbeat_sandbox_not_found_re_registering",
                            "sandbox_id": current_sandbox_id,
                        },
                    )
                    current_sandbox_id = await register_with_controller(
                        sandbox_id=sandbox_id,
                        controller_url=controller_url,
                        sandbox_url=sandbox_url,
                        labels=labels,
                    )
                else:
                    resp.raise_for_status()
                    logger.debug(
                        "heartbeat_sent",
                        extra={
                            "event": "heartbeat_sent",
                            "sandbox_id": current_sandbox_id,
                        },
                    )
        except Exception as exc:
            logger.warning(
                "heartbeat_failed",
                extra={"event": "heartbeat_failed", "error": str(exc)},
            )
