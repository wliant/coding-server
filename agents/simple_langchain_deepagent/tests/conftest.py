from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def tmp_working_dir(tmp_path: Path) -> Path:
    """Return a temporary directory path for use as the agent working directory."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    return work_dir


@pytest.fixture()
def fake_llm():
    """Return a mock LLM for testing (no real connection made)."""
    from unittest.mock import MagicMock
    from langchain_core.messages import AIMessage

    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="def hello(): pass")
    return llm


@pytest.fixture()
def mock_llm_call(mocker):
    """Patch langchain_core model invocation to return a canned response.

    Prevents real HTTP requests to Ollama or other LLM providers during tests.
    """
    from langchain_core.messages import AIMessage

    canned_content = "def placeholder():\n    pass\n"
    mock = mocker.MagicMock()
    mock.invoke.return_value = {"messages": [AIMessage(content=canned_content)]}
    return mock
