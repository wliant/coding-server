"""In-memory worker registry for the Controller."""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger(__name__)


WorkerStatus = Literal["free", "in_progress", "completed", "failed", "unreachable"]


@dataclass
class WorkerRecord:
    worker_id: str
    agent_type: str
    worker_url: str
    status: WorkerStatus
    last_heartbeat_at: datetime
    registered_at: datetime
    current_task_id: str | None = None


class WorkerRegistry:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._workers: dict[str, WorkerRecord] = {}

    async def register(self, worker_id: str, agent_type: str, worker_url: str) -> str:
        """Register a worker using the worker-proposed ID.

        Deduplicates by both URL (handles IP change) and worker_id (handles restart).
        Returns the worker_id unchanged.
        """
        async with self._lock:
            # Remove any existing record with the same URL or same worker_id
            for wid, rec in list(self._workers.items()):
                if rec.worker_url == worker_url or wid == worker_id:
                    if wid != worker_id:
                        logger.warning(
                            "worker_id_collision",
                            extra={
                                "event": "worker_id_collision",
                                "new_worker_id": worker_id,
                                "existing_worker_id": wid,
                            },
                        )
                    del self._workers[wid]
            now = datetime.now(timezone.utc)
            self._workers[worker_id] = WorkerRecord(
                worker_id=worker_id,
                agent_type=agent_type,
                worker_url=worker_url,
                status="free",
                last_heartbeat_at=now,
                registered_at=now,
            )
            return worker_id

    async def heartbeat(
        self,
        worker_id: str,
        status: WorkerStatus,
        task_id: str | None = None,
    ) -> bool:
        """Update heartbeat. Returns False if worker_id not found."""
        async with self._lock:
            rec = self._workers.get(worker_id)
            if rec is None:
                return False
            rec.last_heartbeat_at = datetime.now(timezone.utc)
            rec.status = status
            rec.current_task_id = task_id
            return True

    async def mark_unreachable(self, worker_id: str) -> None:
        async with self._lock:
            rec = self._workers.get(worker_id)
            if rec:
                rec.status = "unreachable"

    async def set_free(self, worker_id: str) -> None:
        async with self._lock:
            rec = self._workers.get(worker_id)
            if rec:
                rec.status = "free"
                rec.current_task_id = None

    async def assign_task(self, worker_id: str, task_id: str) -> None:
        async with self._lock:
            rec = self._workers.get(worker_id)
            if rec:
                rec.status = "in_progress"
                rec.current_task_id = task_id

    async def get_free_worker_for_agent_type(self, agent_type: str) -> WorkerRecord | None:
        async with self._lock:
            for rec in self._workers.values():
                if rec.agent_type == agent_type and rec.status == "free":
                    return rec
            return None

    async def get_stale_workers(self, timeout_seconds: int) -> list[WorkerRecord]:
        """Return workers whose last heartbeat is older than timeout_seconds."""
        now = datetime.now(timezone.utc)
        async with self._lock:
            return [
                rec
                for rec in self._workers.values()
                if rec.status not in ("unreachable",)
                and (now - rec.last_heartbeat_at).total_seconds() > timeout_seconds
            ]

    async def get_all(self) -> list[WorkerRecord]:
        async with self._lock:
            return list(self._workers.values())

    async def get(self, worker_id: str) -> WorkerRecord | None:
        async with self._lock:
            return self._workers.get(worker_id)
