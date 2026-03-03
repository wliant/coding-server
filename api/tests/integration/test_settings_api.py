"""Integration tests for /settings API endpoints."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.models.project import Base
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

    with patch("api.main.aioredis.Redis.from_url") as mock_redis_cls:
        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()
        mock_redis_cls.return_value = mock_redis
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


async def test_get_settings_returns_defaults_when_empty(client):
    """GET /settings returns 200 with default values when no rows exist."""
    response = await client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    assert data == {"settings": {"agent.work.path": ""}}


async def test_put_settings_valid_key_returns_200(client):
    """PUT /settings with valid key returns 200 with updated value."""
    response = await client.put(
        "/settings",
        json={"settings": {"agent.work.path": "/home/user/work"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["agent.work.path"] == "/home/user/work"


async def test_get_settings_reflects_saved_value(client):
    """GET /settings reflects previously saved value."""
    # Save a value first
    await client.put(
        "/settings",
        json={"settings": {"agent.work.path": "/custom/path"}},
    )

    response = await client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["agent.work.path"] == "/custom/path"


async def test_put_settings_unknown_key_returns_422(client):
    """PUT /settings with unknown key returns 422."""
    response = await client.put(
        "/settings",
        json={"settings": {"unknown.key": "some-value"}},
    )
    assert response.status_code == 422
