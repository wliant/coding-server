from unittest.mock import MagicMock

import pytest
import fakeredis.aioredis
from langchain_core.messages import AIMessage


@pytest.fixture
def base_state() -> dict:
    """Minimal AgentState dict for worker unit tests."""
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
    """Mock LLM that returns a fixed AIMessage."""
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="test response")
    return llm


@pytest.fixture
async def fake_redis():
    """In-memory Redis substitute for worker unit tests."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()
