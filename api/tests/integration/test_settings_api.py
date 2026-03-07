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


ALL_DEFAULT_KEYS = {
    "agent.work.path",
    "agent.simple_crewai.llm_provider",
    "agent.simple_crewai.llm_model",
    "agent.simple_crewai.llm_temperature",
    "agent.simple_crewai.ollama_base_url",
    "agent.simple_crewai.openai_api_key",
    "agent.simple_crewai.anthropic_api_key",
}


async def test_get_settings_returns_defaults_when_empty(client):
    """GET /settings returns 200 with all 7 default keys when no rows exist."""
    response = await client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    assert set(data["settings"].keys()) == ALL_DEFAULT_KEYS
    assert data["settings"]["agent.work.path"] == ""
    assert data["settings"]["agent.simple_crewai.llm_provider"] == "ollama"
    assert data["settings"]["agent.simple_crewai.llm_model"] == "qwen2.5-coder:7b"
    assert data["settings"]["agent.simple_crewai.llm_temperature"] == "0.2"
    assert data["settings"]["agent.simple_crewai.ollama_base_url"] == "http://localhost:11434"


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


# --- New agent settings keys ---

async def test_put_settings_all_six_agent_keys_returns_200(client):
    """PUT /settings with all 6 new agent keys returns 200."""
    response = await client.put(
        "/settings",
        json={
            "settings": {
                "agent.simple_crewai.llm_provider": "openai",
                "agent.simple_crewai.llm_model": "gpt-4o",
                "agent.simple_crewai.llm_temperature": "0.5",
                "agent.simple_crewai.ollama_base_url": "http://my-ollama:11434",
                "agent.simple_crewai.openai_api_key": "sk-abc",
                "agent.simple_crewai.anthropic_api_key": "ant-xyz",
            }
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["agent.simple_crewai.llm_provider"] == "openai"
    assert data["settings"]["agent.simple_crewai.llm_model"] == "gpt-4o"
    assert data["settings"]["agent.simple_crewai.openai_api_key"] == "sk-abc"


async def test_put_settings_invalid_provider_returns_422(client):
    """PUT /settings with unsupported llm_provider returns 422."""
    response = await client.put(
        "/settings",
        json={"settings": {"agent.simple_crewai.llm_provider": "mistral"}},
    )
    assert response.status_code == 422


async def test_put_settings_invalid_temperature_non_numeric_returns_422(client):
    """PUT /settings with non-numeric llm_temperature returns 422."""
    response = await client.put(
        "/settings",
        json={"settings": {"agent.simple_crewai.llm_temperature": "hot"}},
    )
    assert response.status_code == 422


async def test_put_settings_invalid_temperature_out_of_range_returns_422(client):
    """PUT /settings with out-of-range llm_temperature returns 422."""
    response = await client.put(
        "/settings",
        json={"settings": {"agent.simple_crewai.llm_temperature": "3.0"}},
    )
    assert response.status_code == 422


async def test_get_settings_returns_all_seven_keys_after_partial_update(client):
    """GET /settings returns all 7 keys even after a partial update."""
    await client.put(
        "/settings",
        json={"settings": {"agent.simple_crewai.llm_provider": "anthropic"}},
    )
    response = await client.get("/settings")
    data = response.json()
    assert set(data["settings"].keys()) == ALL_DEFAULT_KEYS
    assert data["settings"]["agent.simple_crewai.llm_provider"] == "anthropic"
    # Other keys should retain defaults
    assert data["settings"]["agent.simple_crewai.llm_model"] == "qwen2.5-coder:7b"
