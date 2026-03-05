import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from crewai import LLM

# Ensure OPENAI_API_KEY is set before any crewai imports so validation passes
os.environ.setdefault("OPENAI_API_KEY", "NA")


@pytest.fixture()
def tmp_working_dir(tmp_path: Path) -> Path:
    """Return a temporary directory path for use as the agent working directory."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    return work_dir


@pytest.fixture()
def fake_llm() -> LLM:
    """Return a real crewai.LLM configured for testing (no real connection made on construction)."""
    return LLM(model="ollama/fake-model", base_url="http://localhost:1", temperature=0.0)


@pytest.fixture()
def mock_llm_call(mocker):
    """Patch litellm.completion to return a canned code response.

    This fixture prevents any real HTTP requests to Ollama or other LLM providers
    during unit and integration tests.
    """
    canned_content = "def placeholder():\n    pass\n"
    return mocker.patch(
        "litellm.completion",
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content=canned_content))],
            usage=MagicMock(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        ),
    )
