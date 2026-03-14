"""Integration tests for /tasks/{id}/files file proxy endpoints."""

import os
import tempfile
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.models.project import Base, Project
from api.models.job import Job, WorkDirectory  # noqa: F401
from api.models.setting import Setting  # noqa: F401
from api.models.agent import Agent  # noqa: F401


@pytest.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = [t for t in Base.metadata.sorted_tables if t.name != "sandboxes"]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=tables)
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


async def test_list_task_files_returns_404_for_unknown_task(client):
    """GET /tasks/{id}/files returns 404 for unknown task."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/tasks/{fake_id}/files")
    assert response.status_code == 404


async def test_get_task_file_content_returns_404_for_unknown_task(client):
    """GET /tasks/{id}/files/{path} returns 404 for unknown task."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/tasks/{fake_id}/files/README.md")
    assert response.status_code == 404


async def test_list_task_files_returns_404_when_no_source(client, test_session):
    """GET /tasks/{id}/files returns 404 for completed task without worker."""
    project = Project(name=None, source_type="new", status="active")
    test_session.add(project)
    await test_session.flush()
    job = Job(project_id=project.id, requirement="test", status="completed")
    test_session.add(job)
    await test_session.commit()
    await test_session.refresh(job)

    response = await client.get(f"/tasks/{job.id}/files")
    assert response.status_code == 404


async def test_list_task_files_pending_with_git_url_clones_repo(client, test_session):
    """GET /tasks/{id}/files for pending task with git_url should attempt clone."""
    project = Project(
        name="Test",
        source_type="existing",
        status="active",
        git_url="https://github.com/octocat/Hello-World.git",
    )
    test_session.add(project)
    await test_session.flush()
    job = Job(project_id=project.id, requirement="test", status="pending")
    test_session.add(job)
    await test_session.commit()
    await test_session.refresh(job)

    # Mock the temp clone to return a local directory
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"))
        with open(os.path.join(tmpdir, "README.md"), "w") as f:
            f.write("# Hello World")
        with open(os.path.join(tmpdir, "src", "main.py"), "w") as f:
            f.write("print('hello')")

        with patch(
            "api.services.file_proxy_service._ensure_temp_clone",
            return_value=tmpdir,
        ):
            response = await client.get(f"/tasks/{job.id}/files")

    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    paths = {e["path"] for e in data["entries"]}
    assert "README.md" in paths
    assert "src" in paths
    assert "src/main.py" in paths


async def test_get_task_file_content_pending_with_git_url(client, test_session):
    """GET /tasks/{id}/files/{path} for pending task reads from clone."""
    project = Project(
        name="Test",
        source_type="existing",
        status="active",
        git_url="https://github.com/octocat/Hello-World.git",
    )
    test_session.add(project)
    await test_session.flush()
    job = Job(project_id=project.id, requirement="test", status="pending")
    test_session.add(job)
    await test_session.commit()
    await test_session.refresh(job)

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "README.md"), "w") as f:
            f.write("# Hello World")

        with patch(
            "api.services.file_proxy_service._ensure_temp_clone",
            return_value=tmpdir,
        ):
            response = await client.get(f"/tasks/{job.id}/files/README.md")

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "# Hello World"
    assert data["is_binary"] is False
    assert data["path"] == "README.md"
