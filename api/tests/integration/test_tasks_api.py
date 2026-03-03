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
