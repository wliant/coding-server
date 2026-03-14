"""Integration tests for GET /agents endpoint. (T008)"""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.models.project import Base
from api.models.job import Job, WorkDirectory  # noqa: F401
from api.models.setting import Setting  # noqa: F401
from api.models.agent import Agent  # noqa: F401


@pytest.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # Exclude sandboxes table — ARRAY(Text) is not supported by SQLite
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


async def test_list_agents_returns_only_active_agents(client, test_session):
    """GET /agents returns only active agents, ordered by display_name."""
    active1 = Agent(identifier="agent_b", display_name="Beta Agent", is_active=True)
    active2 = Agent(identifier="agent_a", display_name="Alpha Agent", is_active=True)
    inactive = Agent(identifier="agent_c", display_name="Zeta Agent", is_active=False)
    test_session.add_all([active1, active2, inactive])
    await test_session.commit()

    response = await client.get("/agents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["display_name"] == "Alpha Agent"
    assert data[1]["display_name"] == "Beta Agent"


async def test_list_agents_returns_empty_when_no_active_agents(client, test_session):
    """GET /agents returns [] when no active agents exist."""
    inactive = Agent(identifier="inactive_agent", display_name="Inactive", is_active=False)
    test_session.add(inactive)
    await test_session.commit()

    response = await client.get("/agents")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_agents_response_shape(client, test_session):
    """GET /agents response includes id, identifier, display_name, is_active, created_at."""
    agent = Agent(identifier="my_agent", display_name="My Agent", is_active=True)
    test_session.add(agent)
    await test_session.commit()
    await test_session.refresh(agent)

    response = await client.get("/agents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    item = data[0]
    assert "id" in item
    assert item["identifier"] == "my_agent"
    assert item["display_name"] == "My Agent"
    assert item["is_active"] is True
    assert "created_at" in item
