"""Integration tests for POST /tasks/{id}/push with git_url body (T026, T027)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models.project import Base, Project
from api.models.job import Job, WorkDirectory  # noqa: F401
from api.models.setting import Setting  # noqa: F401
from api.models.agent import Agent  # noqa: F401


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
    from api.main import app
    from api.db import get_db

    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("api.main.aioredis.Redis.from_url") as mock_redis_cls:
        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()
        mock_redis_cls.return_value = mock_redis
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


async def test_push_with_git_url_body_saves_url_and_returns_200(client, test_session):
    """POST /tasks/{id}/push with git_url body updates project.git_url and returns 200."""
    from api.schemas.task import PushResponse

    project = Project(name="New Project", source_type="new", status="active", git_url=None)
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

    wd = WorkDirectory(job_id=job.id, path="/agent-work/push-test")
    test_session.add(wd)
    await test_session.commit()
    await test_session.refresh(job)

    pushed_at = datetime.now(timezone.utc)
    mock_push_result = PushResponse(
        branch_name=f"task/{str(job.id)[:8]}",
        remote_url="https://github.com/org/new-repo.git",
        pushed_at=pushed_at,
    )

    with patch("api.services.task_service.git_service") as mock_git:
        mock_git.push_working_directory_to_remote.return_value = mock_push_result
        response = await client.post(
            f"/tasks/{job.id}/push",
            json={"git_url": "https://github.com/org/new-repo.git"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["remote_url"] == "https://github.com/org/new-repo.git"
    assert "branch_name" in data

    # Verify the project git_url was persisted
    await test_session.refresh(project)
    assert project.git_url == "https://github.com/org/new-repo.git"


async def test_push_without_body_uses_stored_url(client, test_session):
    """POST /tasks/{id}/push with no body uses the project's stored git_url."""
    from api.schemas.task import PushResponse

    project = Project(
        name="Stored URL Project",
        source_type="new",
        status="active",
        git_url="https://github.com/org/stored-repo.git",
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

    wd = WorkDirectory(job_id=job.id, path="/agent-work/stored-url-test")
    test_session.add(wd)
    await test_session.commit()
    await test_session.refresh(job)

    pushed_at = datetime.now(timezone.utc)
    mock_push_result = PushResponse(
        branch_name=f"task/{str(job.id)[:8]}",
        remote_url="https://github.com/org/stored-repo.git",
        pushed_at=pushed_at,
    )

    with patch("api.services.task_service.git_service") as mock_git:
        mock_git.push_working_directory_to_remote.return_value = mock_push_result
        response = await client.post(f"/tasks/{job.id}/push")

    assert response.status_code == 200
    data = response.json()
    assert data["remote_url"] == "https://github.com/org/stored-repo.git"
