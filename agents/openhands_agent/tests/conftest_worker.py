from unittest.mock import MagicMock

import pytest


@pytest.fixture
def base_state() -> dict:
    """Minimal state dict for worker unit tests."""
    return {
        "job_id": "test-job-id",
        "requirement": "Build a hello world app",
        "messages": [],
        "tool_calls": [],
        "output": None,
        "error": None,
    }


@pytest.fixture
def mock_llm():
    """Mock LLM that returns a fixed response."""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="test response")
    return llm


@pytest.fixture
async def db_session():
    """SQLite in-memory session for worker unit tests that need DB access."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from worker.models import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()
