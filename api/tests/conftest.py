import pytest
import fakeredis.aioredis


@pytest.fixture
async def fake_redis():
    """In-memory Redis substitute for unit tests."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def db_session():
    """SQLite in-memory session for unit tests that need DB access."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from api.models.project import Base
    from api.models.job import Job, WorkDirectory  # noqa: F401

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()
