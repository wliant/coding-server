"""Integration tests for POST /tasks with agent_id (T009, T010, T011)."""
import uuid
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


@pytest.fixture
async def seeded_agent(test_session) -> Agent:
    """Seed one active agent and return it."""
    agent = Agent(identifier="spec_driven_development", display_name="Spec-Driven Development", is_active=True)
    test_session.add(agent)
    await test_session.commit()
    await test_session.refresh(agent)
    return agent


async def test_create_task_new_project_with_agent_returns_201(client, test_session, seeded_agent):
    """POST /tasks with project_type='new', project_name, and agent_id returns 201."""
    payload = {
        "project_type": "new",
        "project_name": "Acme App",
        "agent_id": str(seeded_agent.id),
        "requirements": "Build a REST API",
    }
    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "pending"
    assert data["project"]["name"] == "Acme App"
    assert data["project"]["source_type"] == "new"
    assert data["agent"] is not None
    assert data["agent"]["identifier"] == "spec_driven_development"
    assert data["requirements"] == "Build a REST API"


async def test_create_task_new_project_missing_project_name_returns_422(client, test_session, seeded_agent):
    """POST /tasks with project_type='new' but no project_name returns 422."""
    payload = {
        "project_type": "new",
        "agent_id": str(seeded_agent.id),
        "requirements": "Build something",
    }
    response = await client.post("/tasks", json=payload)
    assert response.status_code == 422
    # Should mention project_name in the error
    detail = str(response.json())
    assert "project_name" in detail.lower() or "project name" in detail.lower()


async def test_create_task_missing_agent_id_returns_422(client, test_session):
    """POST /tasks without agent_id returns 422."""
    payload = {
        "project_type": "new",
        "project_name": "Test",
        "requirements": "Do something",
    }
    response = await client.post("/tasks", json=payload)
    assert response.status_code == 422
    detail = str(response.json())
    assert "agent_id" in detail.lower() or "agent" in detail.lower()


async def test_create_task_new_project_with_git_url_saves_url(client, test_session, seeded_agent):
    """POST /tasks with project_type='new' and git_url stores the URL on the project."""
    payload = {
        "project_type": "new",
        "project_name": "My Repo Project",
        "agent_id": str(seeded_agent.id),
        "git_url": "https://github.com/org/my-repo",
        "requirements": "Build it",
    }
    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["project"]["git_url"] == "https://github.com/org/my-repo"
