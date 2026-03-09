import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.agent import Agent
from api.models.job import Job, WorkDirectory
from api.models.project import Project
from api.schemas.task import CreateTaskRequest, PushResponse, UpdateTaskRequest
from api.services import git_service, setting_service
from api.services.project_service import create_project


def _inject_github_token(url: str, token: str) -> str:
    """Inject GitHub token into HTTPS URL for authenticated git operations."""
    if token and url.startswith("https://github.com"):
        return url.replace("https://", f"https://{token}@", 1)
    return url


async def create_task(
    db: AsyncSession, req: CreateTaskRequest
) -> tuple[Job, Project, Agent | None]:
    """Create a task (Job) and optionally a new Project.

    Returns (job, project, agent | None) tuple.
    """
    source_type = req.project_type.value  # "new" or "existing"
    project = await create_project(db, source_type=source_type)
    if req.project_name:
        project.name = req.project_name
    if req.git_url is not None:
        project.git_url = req.git_url

    now = datetime.now(timezone.utc)
    job = Job(
        project_id=project.id,
        requirement=req.requirements,
        agent_id=req.agent_id,
        branch=req.branch,
        status="pending",
        updated_at=now,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    await db.commit()

    # Load the agent for the response
    agent = await _load_agent(db, req.agent_id)

    return job, project, agent


async def _load_agent(db: AsyncSession, agent_id: uuid.UUID | None) -> Agent | None:
    if agent_id is None:
        return None
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def list_tasks(db: AsyncSession) -> list[tuple[Job, Project, Agent | None]]:
    """Return all jobs joined with their projects and agents, ordered by created_at DESC."""
    result = await db.execute(
        select(Job, Project, Agent)
        .join(Project, Job.project_id == Project.id)
        .outerjoin(Agent, Job.agent_id == Agent.id)
        .order_by(Job.created_at.desc())
    )
    return list(result.all())


async def get_task_detail(
    db: AsyncSession, task_id: uuid.UUID
) -> tuple[Job, Project, WorkDirectory | None, Agent | None] | None:
    """Return (job, project, work_directory | None, agent | None) for the given task_id.

    Returns None if the task does not exist.
    """
    result = await db.execute(
        select(Job, Project, Agent)
        .join(Project, Job.project_id == Project.id)
        .outerjoin(Agent, Job.agent_id == Agent.id)
        .where(Job.id == task_id)
    )
    row = result.one_or_none()
    if row is None:
        return None

    job, project, agent = row

    wd_result = await db.execute(
        select(WorkDirectory).where(WorkDirectory.job_id == task_id)
    )
    work_directory = wd_result.scalar_one_or_none()

    return job, project, work_directory, agent


async def trigger_push(
    db: AsyncSession,
    task_id: uuid.UUID,
    git_url_override: str | None = None,
) -> PushResponse:
    """Push a completed task's working directory to the remote git repository.

    If the task has an assigned worker, proxies the push request to that worker.
    Otherwise falls back to calling git_service directly (legacy path).

    Raises:
        HTTPException 404: task not found
        HTTPException 409: task is not Completed
        HTTPException 422: project has no git_url (and none provided)
        HTTPException 502: git push failed
    """
    import httpx

    detail = await get_task_detail(db, task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Task not found")

    job, project, work_directory, _agent = detail

    if job.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Task is not completed (current status: {job.status})",
        )

    # Save git_url to project if an override is provided
    if git_url_override is not None:
        project.git_url = git_url_override
        await db.flush()

    effective_git_url = project.git_url

    # If the task was handled by a worker, proxy push to that worker
    if job.assigned_worker_url:
        try:
            # Always re-fetch the token from settings so push works even after a
            # worker restart (in-memory token is lost on restart)
            push_settings = await setting_service.get_settings(db)
            github_token = push_settings.get("github.token") or None
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{job.assigned_worker_url}/push",
                    json={"git_url": git_url_override, "github_token": github_token},
                )
                resp.raise_for_status()
                data = resp.json()
                return PushResponse(
                    branch_name=data["branch_name"],
                    remote_url=data["remote_url"],
                    pushed_at=data["pushed_at"],
                )
        except httpx.HTTPStatusError as exc:
            detail_msg = exc.response.text
            raise HTTPException(status_code=502, detail=f"Worker push failed: {detail_msg}") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Worker push failed: {exc}") from exc

    # Legacy path: push directly from API server
    if effective_git_url is None:
        raise HTTPException(
            status_code=422, detail="Project has no git_url configured"
        )

    if work_directory is None:
        raise HTTPException(
            status_code=422, detail="No working directory found for this task"
        )

    settings = await setting_service.get_settings(db)
    github_token = settings.get("github.token", "")
    effective_git_url = _inject_github_token(effective_git_url, github_token)

    branch_name = f"task/{str(task_id)[:8]}"

    try:
        result = git_service.push_working_directory_to_remote(
            work_dir_path=work_directory.path,
            remote_url=effective_git_url,
            branch_name=branch_name,
        )
        await db.commit()
        return result
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Git push failed: {exc}") from exc


async def download_task_code(db: AsyncSession, task_id: uuid.UUID) -> tuple[bytes, str]:
    """Proxy zip download from assigned worker.

    Returns (zip_bytes, filename).
    Raises HTTPException 404 if task not found, 409 if no worker assigned.
    """
    import httpx

    result = await db.execute(select(Job).where(Job.id == task_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not job.assigned_worker_url:
        raise HTTPException(status_code=409, detail="No worker assigned to this task")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{job.assigned_worker_url}/download")
        resp.raise_for_status()

    filename = f"task-{str(task_id)[:8]}.zip"
    return resp.content, filename


async def initiate_cleanup(db: AsyncSession, task_id: uuid.UUID) -> Job:
    """Initiate cleanup for a completed or failed task.

    Sets status to 'cleaning_up'. The controller will detect this and call
    the worker's /free endpoint to delete the working directory.

    Raises:
        HTTPException 404: task not found
        HTTPException 409: task is not completed or failed
    """
    result = await db.execute(select(Job).where(Job.id == task_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if job.status not in ("completed", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Can only clean up completed or failed tasks (current status: {job.status})",
        )

    job.status = "cleaning_up"
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job


async def abort_task(
    db: AsyncSession, task_id: uuid.UUID
) -> tuple[Job, Project, Agent | None]:
    """Abort a pending task. Raises 404 if not found, 422 if not pending."""
    result = await db.execute(
        select(Job, Project, Agent)
        .join(Project, Job.project_id == Project.id)
        .outerjoin(Agent, Job.agent_id == Agent.id)
        .where(Job.id == task_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    job, project, agent = row
    if job.status != "pending":
        raise HTTPException(
            status_code=422, detail="Can only abort pending tasks"
        )

    job.status = "aborted"
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job, project, agent


async def resubmit_task(
    db: AsyncSession, task_id: uuid.UUID, updates: UpdateTaskRequest
) -> tuple[Job, Project, Agent | None]:
    """Resubmit an aborted task. Raises 404 if not found, 422 if not aborted."""
    result = await db.execute(
        select(Job, Project, Agent)
        .join(Project, Job.project_id == Project.id)
        .outerjoin(Agent, Job.agent_id == Agent.id)
        .where(Job.id == task_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    job, project, agent = row
    if job.status != "aborted":
        raise HTTPException(
            status_code=422, detail="Can only resubmit aborted tasks"
        )

    # Apply updates
    if updates.requirements is not None:
        job.requirement = updates.requirements
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
    return job, project, agent
