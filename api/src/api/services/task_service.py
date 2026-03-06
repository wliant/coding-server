import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.job import Job, WorkDirectory
from api.models.project import Project
from api.schemas.task import CreateTaskRequest, PushResponse, UpdateTaskRequest
from api.services import git_service
from api.services.project_service import create_project


async def create_task(
    db: AsyncSession, req: CreateTaskRequest
) -> tuple[Job, Project]:
    """Create a task (Job) and optionally a new Project.

    Returns (job, project) tuple.
    """
    if req.project_type.value == "new":
        project = await create_project(db, source_type="new")
        if req.git_url is not None:
            project.git_url = req.git_url
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


async def get_task_detail(
    db: AsyncSession, task_id: uuid.UUID
) -> tuple[Job, Project, WorkDirectory | None] | None:
    """Return (job, project, work_directory | None) for the given task_id.

    Returns None if the task does not exist.
    """
    result = await db.execute(
        select(Job, Project)
        .join(Project, Job.project_id == Project.id)
        .where(Job.id == task_id)
    )
    row = result.one_or_none()
    if row is None:
        return None

    job, project = row

    wd_result = await db.execute(
        select(WorkDirectory).where(WorkDirectory.job_id == task_id)
    )
    work_directory = wd_result.scalar_one_or_none()

    return job, project, work_directory


async def trigger_push(
    db: AsyncSession, task_id: uuid.UUID
) -> PushResponse:
    """Push a completed task's working directory to the remote git repository.

    Raises:
        HTTPException 404: task not found
        HTTPException 409: task is not Completed
        HTTPException 422: project has no git_url
        HTTPException 502: git push failed
    """
    detail = await get_task_detail(db, task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Task not found")

    job, project, work_directory = detail

    if job.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Task is not completed (current status: {job.status})",
        )

    if project.git_url is None:
        raise HTTPException(
            status_code=422, detail="Project has no git_url configured"
        )

    if work_directory is None:
        raise HTTPException(
            status_code=422, detail="No working directory found for this task"
        )

    branch_name = f"task/{str(task_id)[:8]}"

    try:
        return git_service.push_working_directory_to_remote(
            work_dir_path=work_directory.path,
            remote_url=project.git_url,
            branch_name=branch_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Git push failed: {exc}") from exc


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
