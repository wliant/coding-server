"""Integration tests for /tasks and /projects API endpoints."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.models.project import Base, Project
from api.models.job import Job, WorkDirectory  # noqa: F401
from api.models.setting import Setting  # noqa: F401


@pytest.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(test_session):
    """Create an ASGI test client with the app dependency overrides."""
    from api.main import app
    from api.db import get_db

    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    # Mock lifespan redis to avoid actual redis connection
    with patch("api.main.aioredis.Redis.from_url") as mock_redis_cls:
        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()
        mock_redis_cls.return_value = mock_redis
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


# ============================================================
# GET /projects tests
# ============================================================

async def test_get_projects_returns_only_named_projects(client, test_session):
    """GET /projects returns only projects where name IS NOT NULL."""
    named = Project(name="Project Alpha", source_type="new", status="active")
    unnamed = Project(name=None, source_type="new", status="active")
    test_session.add(named)
    test_session.add(unnamed)
    await test_session.commit()

    response = await client.get("/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Project Alpha"


async def test_get_projects_empty_when_no_named_projects(client, test_session):
    """GET /projects returns [] when no named projects exist."""
    unnamed = Project(name=None, source_type="new", status="active")
    test_session.add(unnamed)
    await test_session.commit()

    response = await client.get("/projects")
    assert response.status_code == 200
    assert response.json() == []


# ============================================================
# POST /tasks tests
# ============================================================

async def test_post_task_new_project_returns_201_with_pending_status(client):
    """POST /tasks with project_type='new' returns 201 with status='pending'."""
    payload = {
        "project_type": "new",
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "Build a REST API for user management",
    }

    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["requirements"] == "Build a REST API for user management"
    assert data["project"]["source_type"] == "new"
    assert "id" in data
    # Validate UUID
    uuid.UUID(data["id"])


async def test_post_task_missing_requirements_returns_422(client):
    """POST /tasks without requirements returns 422."""
    payload = {
        "project_type": "new",
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
    }

    response = await client.post("/tasks", json=payload)
    assert response.status_code == 422


async def test_post_task_empty_requirements_returns_422(client):
    """POST /tasks with empty requirements returns 422."""
    payload = {
        "project_type": "new",
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "",
    }

    response = await client.post("/tasks", json=payload)
    assert response.status_code == 422


async def test_post_task_existing_invalid_project_id_returns_422(client):
    """POST /tasks with project_type='existing' and non-existent project_id returns 422."""
    payload = {
        "project_type": "existing",
        "project_id": str(uuid.uuid4()),
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "Do something with the project",
    }

    response = await client.post("/tasks", json=payload)
    assert response.status_code == 422


async def test_post_task_existing_project_creates_task(client, test_session):
    """POST /tasks with project_type='existing' and valid project_id returns 201."""
    # Create a project first
    project = Project(name="My Project", source_type="existing", status="active")
    test_session.add(project)
    await test_session.commit()
    await test_session.refresh(project)

    payload = {
        "project_type": "existing",
        "project_id": str(project.id),
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "Add login functionality",
    }

    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["project"]["id"] == str(project.id)


# ============================================================
# GET /tasks tests
# ============================================================

async def test_get_tasks_returns_empty_when_no_tasks(client):
    """GET /tasks returns [] when no tasks exist."""
    response = await client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_tasks_returns_all_tasks_ordered_by_created_at_desc(client):
    """GET /tasks returns all tasks ordered by created_at DESC."""
    # Create two tasks
    payload1 = {
        "project_type": "new",
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "First task",
    }
    payload2 = {
        "project_type": "new",
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "Second task",
    }

    r1 = await client.post("/tasks", json=payload1)
    r2 = await client.post("/tasks", json=payload2)
    assert r1.status_code == 201
    assert r2.status_code == 201

    response = await client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Most recent first
    assert data[0]["requirements"] == "Second task"
    assert data[1]["requirements"] == "First task"


async def test_get_tasks_includes_project_object(client):
    """GET /tasks response includes project object with name and source_type."""
    payload = {
        "project_type": "new",
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "Build something",
    }

    await client.post("/tasks", json=payload)

    response = await client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "project" in data[0]
    assert "source_type" in data[0]["project"]
    assert "name" in data[0]["project"]


# ============================================================
# PATCH /tasks/{id} abort tests
# ============================================================

async def test_patch_task_abort_pending_returns_200_aborted(client):
    """PATCH /tasks/{id} with status='aborted' on pending task returns 200 with status='aborted'."""
    # Create a task first
    create_payload = {
        "project_type": "new",
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "Task to abort",
    }
    create_response = await client.post("/tasks", json=create_payload)
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    response = await client.patch(f"/tasks/{task_id}", json={"status": "aborted"})
    assert response.status_code == 200
    assert response.json()["status"] == "aborted"


async def test_patch_task_abort_non_pending_returns_422(client, test_session):
    """PATCH /tasks/{id} abort on in_progress task returns 422."""
    # Setup: create a project and a non-pending job directly
    project = Project(name=None, source_type="new", status="active")
    test_session.add(project)
    await test_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Running task",
        status="in_progress",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    test_session.add(job)
    await test_session.commit()
    await test_session.refresh(job)

    response = await client.patch(f"/tasks/{job.id}", json={"status": "aborted"})
    assert response.status_code == 422


async def test_patch_task_abort_non_existent_returns_404(client):
    """PATCH /tasks/{id} on non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.patch(f"/tasks/{fake_id}", json={"status": "aborted"})
    assert response.status_code == 404


# ============================================================
# PATCH /tasks/{id} resubmit tests
# ============================================================

async def test_patch_task_resubmit_aborted_returns_200_pending(client):
    """PATCH /tasks/{id} resubmit on aborted task returns 200 with updated fields and status='pending'."""
    # Create a task
    create_payload = {
        "project_type": "new",
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "Original requirement",
    }
    create_response = await client.post("/tasks", json=create_payload)
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    # Abort it
    abort_response = await client.patch(f"/tasks/{task_id}", json={"status": "aborted"})
    assert abort_response.status_code == 200

    # Resubmit it
    response = await client.patch(
        f"/tasks/{task_id}",
        json={"status": "pending", "requirements": "Updated requirement"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["requirements"] == "Updated requirement"


async def test_patch_task_resubmit_non_aborted_returns_422(client):
    """PATCH /tasks/{id} resubmit on non-aborted task returns 422."""
    # Create a pending task
    create_payload = {
        "project_type": "new",
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "Some task",
    }
    create_response = await client.post("/tasks", json=create_payload)
    task_id = create_response.json()["id"]

    # Try to resubmit (it's pending, not aborted)
    response = await client.patch(
        f"/tasks/{task_id}",
        json={"status": "pending", "requirements": "Updated"},
    )
    assert response.status_code == 422


async def test_patch_task_resubmit_non_existent_returns_404(client):
    """PATCH /tasks/{id} resubmit on non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.patch(
        f"/tasks/{fake_id}", json={"status": "pending", "requirements": "Updated"}
    )
    assert response.status_code == 404


# ============================================================
# GET /tasks/{id} detail tests (T015)
# ============================================================


async def test_get_task_detail_returns_200_with_task_detail_shape(client):
    """GET /tasks/{id} returns 200 with TaskDetailResponse shape."""
    create_payload = {
        "project_type": "new",
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "Build a detail endpoint",
    }
    create_response = await client.post("/tasks", json=create_payload)
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    response = await client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == task_id
    assert data["requirements"] == "Build a detail endpoint"
    assert data["status"] == "pending"
    assert "project" in data
    assert "git_url" in data["project"]
    assert "started_at" in data
    assert "completed_at" in data
    assert "work_directory_path" in data
    assert "elapsed_seconds" in data
    assert data["work_directory_path"] is None
    assert data["elapsed_seconds"] is None


async def test_get_task_detail_returns_404_for_unknown_id(client):
    """GET /tasks/{id} returns 404 for a non-existent task ID."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/tasks/{fake_id}")
    assert response.status_code == 404


async def test_get_task_detail_includes_elapsed_seconds_for_in_progress(client, test_session):
    """GET /tasks/{id} includes elapsed_seconds for in_progress tasks."""
    from datetime import datetime, timezone, timedelta

    project = Project(name=None, source_type="new", status="active")
    test_session.add(project)
    await test_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Running task",
        status="in_progress",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
        started_at=datetime.now(timezone.utc) - timedelta(seconds=30),
    )
    test_session.add(job)
    await test_session.commit()
    await test_session.refresh(job)

    response = await client.get(f"/tasks/{job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["elapsed_seconds"] is not None
    assert data["elapsed_seconds"] >= 30


async def test_get_task_detail_work_directory_path_is_null_before_worker_claims(client):
    """GET /tasks/{id} has work_directory_path=null for a pending task."""
    create_payload = {
        "project_type": "new",
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "Pending task",
    }
    response = await client.post("/tasks", json=create_payload)
    task_id = response.json()["id"]

    detail = await client.get(f"/tasks/{task_id}")
    assert detail.status_code == 200
    assert detail.json()["work_directory_path"] is None


# ============================================================
# POST /tasks/{id}/push tests (T023)
# ============================================================


async def test_push_returns_409_when_task_not_completed(client):
    """POST /tasks/{id}/push returns 409 when task is not Completed."""
    create_payload = {
        "project_type": "new",
        "dev_agent_type": "spec_driven_development",
        "test_agent_type": "generic_testing",
        "requirements": "Pending task",
    }
    response = await client.post("/tasks", json=create_payload)
    task_id = response.json()["id"]

    push_response = await client.post(f"/tasks/{task_id}/push")
    assert push_response.status_code == 409


async def test_push_returns_404_for_unknown_task(client):
    """POST /tasks/{id}/push returns 404 for unknown task."""
    fake_id = str(uuid.uuid4())
    response = await client.post(f"/tasks/{fake_id}/push")
    assert response.status_code == 404


async def test_push_returns_422_when_project_has_no_git_url(client, test_session):
    """POST /tasks/{id}/push returns 422 when project.git_url is None."""
    project = Project(name=None, source_type="new", status="active", git_url=None)
    test_session.add(project)
    await test_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Completed task",
        status="completed",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    test_session.add(job)
    await test_session.commit()
    await test_session.refresh(job)

    response = await client.post(f"/tasks/{job.id}/push")
    assert response.status_code == 422


async def test_push_returns_200_with_push_response_shape_on_success(client, test_session):
    """POST /tasks/{id}/push returns 200 with PushResponse when push succeeds (mocked)."""
    from unittest.mock import patch, AsyncMock
    from datetime import datetime, timezone

    project = Project(
        name="my-proj",
        source_type="new",
        status="active",
        git_url="https://github.com/org/repo.git",
    )
    test_session.add(project)
    await test_session.flush()

    job = Job(
        project_id=project.id,
        requirement="Completed task",
        status="completed",
        dev_agent_type="spec_driven_development",
        test_agent_type="generic_testing",
    )
    test_session.add(job)
    await test_session.flush()

    from api.models.job import WorkDirectory
    wd = WorkDirectory(job_id=job.id, path="/agent-work/abc123")
    test_session.add(wd)
    await test_session.commit()
    await test_session.refresh(job)

    pushed_at = datetime.now(timezone.utc)
    from api.schemas.task import PushResponse
    mock_push_result = PushResponse(
        branch_name=f"task/{str(job.id)[:8]}",
        remote_url="https://github.com/org/repo.git",
        pushed_at=pushed_at,
    )

    with patch("api.services.task_service.git_service") as mock_git:
        mock_git.push_working_directory_to_remote.return_value = mock_push_result
        response = await client.post(f"/tasks/{job.id}/push")

    assert response.status_code == 200
    data = response.json()
    assert "branch_name" in data
    assert "remote_url" in data
    assert "pushed_at" in data
    assert data["branch_name"] == f"task/{str(job.id)[:8]}"
