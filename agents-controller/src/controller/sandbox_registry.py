"""In-memory sandbox registry for the Controller."""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger(__name__)

SandboxStatus = Literal["free", "allocated", "unavailable", "unreachable"]


@dataclass
class SandboxRecord:
    sandbox_id: str
    sandbox_url: str
    labels: list[str]
    status: SandboxStatus
    last_heartbeat_at: datetime
    registered_at: datetime
    current_task_id: str | None = None


class SandboxRegistry:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._sandboxes: dict[str, SandboxRecord] = {}

    async def register(
        self, sandbox_id: str, sandbox_url: str, labels: list[str] | None = None
    ) -> str:
        async with self._lock:
            # Remove any existing record with same URL or same sandbox_id
            for sid, rec in list(self._sandboxes.items()):
                if rec.sandbox_url == sandbox_url or sid == sandbox_id:
                    del self._sandboxes[sid]
            now = datetime.now(timezone.utc)
            self._sandboxes[sandbox_id] = SandboxRecord(
                sandbox_id=sandbox_id,
                sandbox_url=sandbox_url,
                labels=labels or [],
                status="free",
                last_heartbeat_at=now,
                registered_at=now,
            )
            return sandbox_id

    async def heartbeat(self, sandbox_id: str, status: SandboxStatus) -> bool:
        async with self._lock:
            rec = self._sandboxes.get(sandbox_id)
            if rec is None:
                return False
            rec.last_heartbeat_at = datetime.now(timezone.utc)
            rec.status = status
            return True

    async def mark_unreachable(self, sandbox_id: str) -> None:
        async with self._lock:
            rec = self._sandboxes.get(sandbox_id)
            if rec:
                rec.status = "unreachable"

    async def get_all(self) -> list[SandboxRecord]:
        async with self._lock:
            return list(self._sandboxes.values())

    async def get_stale_sandboxes(self, timeout_seconds: int) -> list[SandboxRecord]:
        now = datetime.now(timezone.utc)
        async with self._lock:
            return [
                rec
                for rec in self._sandboxes.values()
                if rec.status not in ("unreachable",)
                and (now - rec.last_heartbeat_at).total_seconds() > timeout_seconds
            ]

    async def get_free_sandbox_for_capabilities(
        self, required: list[str] | None
    ) -> SandboxRecord | None:
        """Find a free sandbox whose labels contain all required capabilities."""
        required_set = set(required) if required else set()
        async with self._lock:
            for rec in self._sandboxes.values():
                if rec.status != "free":
                    continue
                if required_set.issubset(set(rec.labels)):
                    return rec
            return None

    async def allocate(self, sandbox_id: str, task_id: str) -> None:
        """Mark a sandbox as allocated for a task."""
        async with self._lock:
            rec = self._sandboxes.get(sandbox_id)
            if rec:
                rec.status = "allocated"
                rec.current_task_id = task_id

    async def free_sandbox(self, sandbox_id: str) -> None:
        """Return a sandbox to the free pool."""
        async with self._lock:
            rec = self._sandboxes.get(sandbox_id)
            if rec:
                rec.status = "free"
                rec.current_task_id = None
