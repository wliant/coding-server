import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.models.job import Job
from api.models.project import Project
from api.schemas.task import (
    CreateTaskRequest,
    DevAgentType,
    ProjectSummary,
    TaskResponse,
    TaskStatus,
    TestAgentType,
    UpdateTaskRequest,
)
from api.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_to_response(job: Job, project: Project) -> TaskResponse:
    """Serialise a Job + Project pair into a TaskResponse."""
    updated_at = job.updated_at if job.updated_at else job.created_at
    # For SQLite tests, created_at/updated_at may be naive datetimes
    created_at = job.created_at
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    if updated_at is None:
        updated_at = created_at

    return TaskResponse(
        id=job.id,
        project=ProjectSummary.model_validate(project),
        dev_agent_type=DevAgentType(job.dev_agent_type),
        test_agent_type=TestAgentType(job.test_agent_type),
        requirements=job.requirement,
        status=TaskStatus(job.status),
        created_at=created_at,
        updated_at=updated_at,
        error_message=job.error_message,
    )


@router.get("", response_model=list[TaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    rows = await task_service.list_tasks(db)
    return [_task_to_response(job, project) for job, project in rows]


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(req: CreateTaskRequest, db: AsyncSession = Depends(get_db)):
    job, project = await task_service.create_task(db, req)
    return _task_to_response(job, project)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID, req: UpdateTaskRequest, db: AsyncSession = Depends(get_db)
):
    if req.status == TaskStatus.aborted:
        job, project = await task_service.abort_task(db, task_id)
    elif req.status == TaskStatus.pending:
        job, project = await task_service.resubmit_task(db, task_id, req)
    else:
        raise HTTPException(
            status_code=422, detail="Invalid status transition requested"
        )
    return _task_to_response(job, project)
