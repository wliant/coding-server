import uuid
from datetime import datetime

import pytest
from fastapi import HTTPException

from api.models.job import Job
from api.models.project import Project
from api.schemas.task import (
    CreateTaskRequest,
    DevAgentType,
    ProjectType,
    TaskStatus,
    TestAgentType,
    UpdateTaskRequest,
)
from api.services import task_service

_AGENT_ID = uuid.uuid4()


async def test_create_task_new_project_creates_both_project_and_job(db_session):
    """create_task with project_type='new' should create a Project and a Job row."""
    req = CreateTaskRequest(
        project_type=ProjectType.new,
        project_name="Test Project",
        agent_id=_AGENT_ID,
        dev_agent_type=DevAgentType.spec_driven_development,
        test_agent_type=TestAgentType.generic_testing,
        requirements="Build a REST API",
    )

    job, project, agent = await task_service.create_task(db_session, req)

    assert job.id is not None
    assert project.id is not None
    assert job.project_id == project.id
    assert job.requirement == "Build a REST API"
    assert job.status == "pending"
    assert project.name == "Test Project"
    assert project.source_type == "new"
    assert agent is None  # agent not seeded in DB


async def test_create_task_existing_project_creates_new_project_and_job(db_session):
    """create_task with project_type='existing' and git_url creates a new Project and Job."""
    req = CreateTaskRequest(
        project_type=ProjectType.existing,
        agent_id=_AGENT_ID,
        git_url="https://github.com/org/existing-repo.git",
        dev_agent_type=DevAgentType.spec_driven_development,
        test_agent_type=TestAgentType.generic_testing,
        requirements="Add feature X",
    )

    job, project, agent = await task_service.create_task(db_session, req)

    assert job.id is not None
    assert project.id is not None
    assert job.project_id == project.id
    assert project.source_type == "existing"
    assert project.git_url == "https://github.com/org/existing-repo.git"
    assert job.status == "pending"


def test_create_task_existing_project_missing_git_url_raises_validation_error():
    """CreateTaskRequest with project_type='existing' and no git_url raises ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        CreateTaskRequest(
            project_type=ProjectType.existing,
            agent_id=_AGENT_ID,
            requirements="Do something",
            dev_agent_type=DevAgentType.spec_driven_development,
            test_agent_type=TestAgentType.generic_testing,
        )

    assert "git_url" in str(exc_info.value).lower()


async def test_abort_task_on_pending_succeeds(db_session):
    """abort_task on a pending job → status becomes 'aborted'."""
    project = Project(name=None, source_type="new", status="active")
    db_session.add(project)
    await db_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Some task",
        status="pending",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    updated_job, updated_project, agent = await task_service.abort_task(db_session, job.id)

    assert updated_job.status == "aborted"


async def test_abort_task_on_in_progress_raises_422(db_session):
    """abort_task on an in_progress job raises 422."""
    project = Project(name=None, source_type="new", status="active")
    db_session.add(project)
    await db_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Some task",
        status="in_progress",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    with pytest.raises(HTTPException) as exc_info:
        await task_service.abort_task(db_session, job.id)

    assert exc_info.value.status_code == 422


async def test_abort_task_on_aborted_raises_422(db_session):
    """abort_task on an already-aborted job raises 422."""
    project = Project(name=None, source_type="new", status="active")
    db_session.add(project)
    await db_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Some task",
        status="aborted",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    with pytest.raises(HTTPException) as exc_info:
        await task_service.abort_task(db_session, job.id)

    assert exc_info.value.status_code == 422


async def test_resubmit_task_on_aborted_returns_to_pending(db_session):
    """resubmit_task on aborted job → status='pending', fields updated."""
    project = Project(name=None, source_type="new", status="active")
    db_session.add(project)
    await db_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Old requirement",
        status="aborted",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    updates = UpdateTaskRequest(
        status=TaskStatus.pending,
        requirements="Updated requirement",
    )

    updated_job, updated_project, agent = await task_service.resubmit_task(
        db_session, job.id, updates
    )

    assert updated_job.status == "pending"
    assert updated_job.requirement == "Updated requirement"


async def test_resubmit_task_on_pending_raises_422(db_session):
    """resubmit_task on a pending job raises 422."""
    project = Project(name=None, source_type="new", status="active")
    db_session.add(project)
    await db_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Some task",
        status="pending",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    updates = UpdateTaskRequest(status=TaskStatus.pending)

    with pytest.raises(HTTPException) as exc_info:
        await task_service.resubmit_task(db_session, job.id, updates)

    assert exc_info.value.status_code == 422


async def test_create_task_new_project_with_git_url_stores_git_url(db_session):
    """create_task with project_type='new' and git_url stores it on the project."""
    req = CreateTaskRequest(
        project_type=ProjectType.new,
        project_name="Repo Project",
        agent_id=_AGENT_ID,
        dev_agent_type=DevAgentType.spec_driven_development,
        test_agent_type=TestAgentType.generic_testing,
        requirements="Build a REST API",
        git_url="https://github.com/org/repo.git",
    )

    job, project, agent = await task_service.create_task(db_session, req)

    assert project.git_url == "https://github.com/org/repo.git"


async def test_create_task_new_project_without_git_url_leaves_git_url_null(db_session):
    """create_task with project_type='new' and no git_url leaves git_url as None."""
    req = CreateTaskRequest(
        project_type=ProjectType.new,
        project_name="No Git Project",
        agent_id=_AGENT_ID,
        dev_agent_type=DevAgentType.spec_driven_development,
        test_agent_type=TestAgentType.generic_testing,
        requirements="Build a REST API",
    )

    job, project, agent = await task_service.create_task(db_session, req)

    assert project.git_url is None


async def test_get_task_detail_returns_job_project_and_no_work_directory(db_session):
    """get_task_detail returns (job, project, None, None) when no WorkDirectory exists."""
    from api.services.task_service import get_task_detail

    project = Project(name="DetailProject", source_type="new", status="active")
    db_session.add(project)
    await db_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Some task",
        status="pending",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    result = await get_task_detail(db_session, job.id)

    assert result is not None
    detail_job, detail_project, work_dir, agent = result
    assert detail_job.id == job.id
    assert detail_project.id == project.id
    assert work_dir is None
    assert agent is None


async def test_get_task_detail_returns_work_directory_when_present(db_session):
    """get_task_detail returns work_directory when one exists for the job."""
    from api.services.task_service import get_task_detail
    from api.models.job import WorkDirectory

    project = Project(name=None, source_type="new", status="active")
    db_session.add(project)
    await db_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Some task",
        status="in_progress",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    db_session.add(job)
    await db_session.flush()

    wd = WorkDirectory(job_id=job.id, path="/agent-work/abc-123")
    db_session.add(wd)
    await db_session.commit()
    await db_session.refresh(job)

    result = await get_task_detail(db_session, job.id)

    assert result is not None
    _, _, work_dir, _ = result
    assert work_dir is not None
    assert work_dir.path == "/agent-work/abc-123"


async def test_get_task_detail_returns_none_for_unknown_id(db_session):
    """get_task_detail returns None for a non-existent task_id."""
    from api.services.task_service import get_task_detail

    result = await get_task_detail(db_session, uuid.uuid4())
    assert result is None


async def test_resubmit_task_on_completed_raises_422(db_session):
    """resubmit_task on a completed job raises 422."""
    project = Project(name=None, source_type="new", status="active")
    db_session.add(project)
    await db_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Some task",
        status="completed",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    updates = UpdateTaskRequest(status=TaskStatus.pending)

    with pytest.raises(HTTPException) as exc_info:
        await task_service.resubmit_task(db_session, job.id, updates)

    assert exc_info.value.status_code == 422
