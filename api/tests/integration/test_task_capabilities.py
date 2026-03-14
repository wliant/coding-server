"""Integration tests for task creation with required_capabilities."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models.project import Base
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


@pytest.fixture
async def seeded_agent(test_session) -> Agent:
    agent = Agent(
        identifier="spec_driven_development",
        display_name="Spec-Driven Development",
        is_active=True,
    )
    test_session.add(agent)
    await test_session.commit()
    await test_session.refresh(agent)
    return agent


async def test_create_task_with_capabilities(client, test_session, seeded_agent):
    """POST /tasks with required_capabilities stores them; GET detail returns them."""
    payload = {
        "task_type": "build_feature",
        "agent_id": str(seeded_agent.id),
        "git_url": "https://github.com/org/repo.git",
        "requirements": "Build a feature requiring python and docker",
        "required_capabilities": ["python", "docker"],
    }
    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201, response.text
    task_id = response.json()["id"]

    detail = await client.get(f"/tasks/{task_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["required_capabilities"] == ["python", "docker"]
    assert data["assigned_sandbox_id"] is None
    assert data["assigned_sandbox_url"] is None


async def test_create_task_without_capabilities(client, test_session, seeded_agent):
    """POST /tasks without required_capabilities defaults to null."""
    payload = {
        "task_type": "build_feature",
        "agent_id": str(seeded_agent.id),
        "git_url": "https://github.com/org/repo.git",
        "requirements": "Simple feature without capabilities",
    }
    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201, response.text
    task_id = response.json()["id"]

    detail = await client.get(f"/tasks/{task_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["required_capabilities"] is None


async def test_task_detail_includes_sandbox_fields(client, test_session, seeded_agent):
    """GET /tasks/{id} includes sandbox fields in response."""
    payload = {
        "task_type": "build_feature",
        "agent_id": str(seeded_agent.id),
        "git_url": "https://github.com/org/repo.git",
        "requirements": "Feature",
        "required_capabilities": ["python"],
    }
    create_resp = await client.post("/tasks", json=payload)
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    detail_resp = await client.get(f"/tasks/{task_id}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()
    assert "required_capabilities" in data
    assert "assigned_sandbox_id" in data
    assert "assigned_sandbox_url" in data
    assert data["required_capabilities"] == ["python"]
