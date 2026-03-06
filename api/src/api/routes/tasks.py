import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.models.job import Job, WorkDirectory
from api.models.project import Project
from api.schemas.task import (
    CreateTaskRequest,
    DevAgentType,
    ProjectSummary,
    ProjectSummaryWithGitUrl,
    PushResponse,
    TaskDetailResponse,
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


def _task_to_detail_response(
    job: Job, project: Project, work_directory: WorkDirectory | None
) -> TaskDetailResponse:
    """Serialise a Job + Project + optional WorkDirectory into a TaskDetailResponse."""
    now = datetime.now(timezone.utc)

    elapsed_seconds: int | None = None
    if job.status == "in_progress" and job.started_at is not None:
        started = job.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        elapsed_seconds = int((now - started).total_seconds())

    return TaskDetailResponse(
        id=job.id,
        project=ProjectSummaryWithGitUrl.model_validate(project),
        dev_agent_type=DevAgentType(job.dev_agent_type),
        test_agent_type=TestAgentType(job.test_agent_type),
        requirements=job.requirement,
        status=TaskStatus(job.status),
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        work_directory_path=work_directory.path if work_directory else None,
        elapsed_seconds=elapsed_seconds,
    )


@router.get("", response_model=list[TaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    rows = await task_service.list_tasks(db)
    return [_task_to_response(job, project) for job, project in rows]


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(req: CreateTaskRequest, db: AsyncSession = Depends(get_db)):
    job, project = await task_service.create_task(db, req)
    return _task_to_response(job, project)


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await task_service.get_task_detail(db, task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    job, project, work_directory = result
    return _task_to_detail_response(job, project, work_directory)


@router.post("/{task_id}/push", response_model=PushResponse)
async def push_task_to_remote(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await task_service.trigger_push(db, task_id)


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
