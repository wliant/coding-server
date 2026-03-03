import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.job import Job
from api.models.project import Project
from api.schemas.task import CreateTaskRequest, UpdateTaskRequest
from api.services.project_service import create_project


async def create_task(
    db: AsyncSession, req: CreateTaskRequest
) -> tuple[Job, Project]:
    """Create a task (Job) and optionally a new Project.

    Returns (job, project) tuple.
    """
    if req.project_type.value == "new":
        project = await create_project(db, source_type="new")
    else:
        # existing project — validate it exists
        result = await db.execute(
            select(Project).where(Project.id == req.project_id)
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=422, detail="Project not found")

    now = datetime.now(timezone.utc)
    job = Job(
        project_id=project.id,
        requirement=req.requirements,
        dev_agent_type=req.dev_agent_type.value,
        test_agent_type=req.test_agent_type.value,
        status="pending",
        updated_at=now,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    await db.commit()

    return job, project


async def list_tasks(db: AsyncSession) -> list[tuple[Job, Project]]:
    """Return all jobs joined with their projects, ordered by created_at DESC."""
    result = await db.execute(
        select(Job, Project)
        .join(Project, Job.project_id == Project.id)
        .order_by(Job.created_at.desc())
    )
    return list(result.all())


async def abort_task(
    db: AsyncSession, task_id: uuid.UUID
) -> tuple[Job, Project]:
    """Abort a pending task. Raises 404 if not found, 422 if not pending."""
    result = await db.execute(
        select(Job, Project)
        .join(Project, Job.project_id == Project.id)
        .where(Job.id == task_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    job, project = row
    if job.status != "pending":
        raise HTTPException(
            status_code=422, detail="Can only abort pending tasks"
        )

    job.status = "aborted"
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job, project


async def resubmit_task(
    db: AsyncSession, task_id: uuid.UUID, updates: UpdateTaskRequest
) -> tuple[Job, Project]:
    """Resubmit an aborted task. Raises 404 if not found, 422 if not aborted."""
    result = await db.execute(
        select(Job, Project)
        .join(Project, Job.project_id == Project.id)
        .where(Job.id == task_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    job, project = row
    if job.status != "aborted":
        raise HTTPException(
            status_code=422, detail="Can only resubmit aborted tasks"
        )

    # Apply updates
    if updates.requirements is not None:
        job.requirement = updates.requirements
    if updates.dev_agent_type is not None:
        job.dev_agent_type = updates.dev_agent_type.value
    if updates.test_agent_type is not None:
        job.test_agent_type = updates.test_agent_type.value
    if updates.project_id is not None:
        # Validate project exists
        proj_result = await db.execute(
            select(Project).where(Project.id == updates.project_id)
        )
        new_project = proj_result.scalar_one_or_none()
        if new_project is None:
            raise HTTPException(status_code=422, detail="Project not found")
        job.project_id = updates.project_id
        project = new_project

    job.status = "pending"
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job, project
