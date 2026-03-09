"""Controller REST API routes."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from controller.registry import WorkerRegistry, WorkerStatus

logger = logging.getLogger(__name__)

router = APIRouter()


class RegisterRequest(BaseModel):
    worker_id: str
    agent_type: str
    worker_url: str


class RegisterResponse(BaseModel):
    worker_id: str


class HeartbeatRequest(BaseModel):
    status: str
    task_id: str | None = None
    error_message: str | None = None


class HeartbeatResponse(BaseModel):
    acknowledged: bool
    should_free: bool = False


class WorkerStatusResponse(BaseModel):
    worker_id: str
    agent_type: str
    worker_url: str
    status: str
    current_task_id: str | None
    registered_at: datetime
    last_heartbeat_at: datetime


def make_router(registry: WorkerRegistry, on_completion_callback=None) -> APIRouter:
    r = APIRouter()

    @r.get("/health")
    async def health():
        return {"status": "ok"}

    @r.post("/workers/register", response_model=RegisterResponse)
    async def register_worker(req: RegisterRequest):
        worker_id = await registry.register(req.worker_id, req.agent_type, req.worker_url)
        logger.info(
            "worker_registered",
            extra={
                "event": "worker_registered",
                "worker_id": worker_id,
                "agent_type": req.agent_type,
                "worker_url": req.worker_url,
            },
        )
        return RegisterResponse(worker_id=worker_id)

    @r.post("/workers/{worker_id}/heartbeat", response_model=HeartbeatResponse)
    async def worker_heartbeat(worker_id: str, req: HeartbeatRequest):
        success = await registry.heartbeat(worker_id, req.status, task_id=req.task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Worker not found — re-registration required")

        # If worker reports completion, trigger callback for DB update
        should_free = False
        if req.status in ("completed", "failed") and on_completion_callback and req.task_id:
            updated = await on_completion_callback(
                worker_id=worker_id,
                task_id=req.task_id,
                status=req.status,
                error_message=req.error_message,
            )
            if not updated:
                should_free = True

        return HeartbeatResponse(acknowledged=True, should_free=should_free)

    @r.get("/workers", response_model=list[WorkerStatusResponse])
    async def list_workers():
        workers = await registry.get_all()
        return [
            WorkerStatusResponse(
                worker_id=w.worker_id,
                agent_type=w.agent_type,
                worker_url=w.worker_url,
                status=w.status,
                current_task_id=w.current_task_id,
                registered_at=w.registered_at,
                last_heartbeat_at=w.last_heartbeat_at,
            )
            for w in workers
        ]

    return r
