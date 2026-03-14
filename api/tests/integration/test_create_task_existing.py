"""Integration tests for POST /tasks with project_type='existing' (T020, T021)."""
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


async def test_create_task_existing_project_with_git_url(client, test_session, seeded_agent):
    """POST /tasks with project_type='existing' and git_url returns 201 with a new project."""
    payload = {
        "task_type": "build_feature",
        "agent_id": str(seeded_agent.id),
        "git_url": "https://github.com/org/original.git",
        "requirements": "Add authentication",
    }
    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "pending"
    assert data["project"]["source_type"] == "existing"
    assert data["project"]["git_url"] == "https://github.com/org/original.git"


async def test_create_task_existing_project_missing_git_url(client, test_session, seeded_agent):
    """POST /tasks with project_type='existing' but no git_url returns 422."""
    payload = {
        "task_type": "build_feature",
        "agent_id": str(seeded_agent.id),
        "requirements": "Do something",
        # git_url intentionally omitted
    }
    response = await client.post("/tasks", json=payload)
    assert response.status_code == 422
    detail = str(response.json())
    assert "git_url" in detail.lower()
