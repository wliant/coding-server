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


async def test_create_task_new_project_creates_both_project_and_job(db_session):
    """create_task with project_type='new' should create a Project and a Job row."""
    req = CreateTaskRequest(
        project_type=ProjectType.new,
        dev_agent_type=DevAgentType.spec_driven_development,
        test_agent_type=TestAgentType.generic_testing,
        requirements="Build a REST API",
    )

    job, project = await task_service.create_task(db_session, req)

    assert job.id is not None
    assert project.id is not None
    assert job.project_id == project.id
    assert job.requirement == "Build a REST API"
    assert job.status == "pending"
    assert project.name is None
    assert project.source_type == "new"


async def test_create_task_existing_project_creates_only_job(db_session):
    """create_task with project_type='existing' and valid project_id creates only a Job."""
    # First create a project
    existing_project = Project(name="Existing", source_type="existing", status="active")
    db_session.add(existing_project)
    await db_session.commit()
    await db_session.refresh(existing_project)

    req = CreateTaskRequest(
        project_type=ProjectType.existing,
        project_id=existing_project.id,
        dev_agent_type=DevAgentType.spec_driven_development,
        test_agent_type=TestAgentType.generic_testing,
        requirements="Add feature X",
    )

    job, project = await task_service.create_task(db_session, req)

    assert job.id is not None
    assert job.project_id == existing_project.id
    assert project.id == existing_project.id
    assert job.status == "pending"


async def test_create_task_existing_invalid_project_raises_422(db_session):
    """create_task with project_type='existing' and invalid project_id raises HTTPException 422."""
    req = CreateTaskRequest(
        project_type=ProjectType.existing,
        project_id=uuid.uuid4(),
        dev_agent_type=DevAgentType.spec_driven_development,
        test_agent_type=TestAgentType.generic_testing,
        requirements="Do something",
    )

    with pytest.raises(HTTPException) as exc_info:
        await task_service.create_task(db_session, req)

    assert exc_info.value.status_code == 422


async def test_abort_task_on_pending_succeeds(db_session):
    """abort_task on a pending job → status becomes 'aborted'."""
    # Setup: create project + pending job
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

    updated_job, updated_project = await task_service.abort_task(db_session, job.id)

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

    updated_job, updated_project = await task_service.resubmit_task(
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
