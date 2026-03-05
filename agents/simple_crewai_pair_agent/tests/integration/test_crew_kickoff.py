"""Integration tests for CodingAgent with mocked LLM — no real Ollama required."""

from pathlib import Path
from unittest.mock import patch

import pytest

from simple_crewai_pair_agent import CodingAgent, CodingAgentConfig


def _make_config(working_directory: Path, project_name: str, requirement: str) -> CodingAgentConfig:
    return CodingAgentConfig(
        working_directory=working_directory,
        project_name=project_name,
        requirement=requirement,
    )


@pytest.fixture()
def fake_llm_patched(fake_llm):
    """Patch make_llm in crew to return the fake_llm fixture."""
    with patch("simple_crewai_pair_agent.crew.make_llm", return_value=fake_llm):
        yield


def test_agent_run_creates_output_file(tmp_working_dir, mock_llm_call, fake_llm_patched):
    cfg = _make_config(tmp_working_dir, "calculator", "write an add function")
    result = CodingAgent(cfg).run()
    assert result.output_file.exists(), "Output file should be written to disk"
    assert result.output_file.stat().st_size > 0, "Output file should be non-empty"


def test_agent_run_returns_non_empty_code(tmp_working_dir, mock_llm_call, fake_llm_patched):
    cfg = _make_config(tmp_working_dir, "calculator", "write an add function")
    result = CodingAgent(cfg).run()
    assert isinstance(result.code, str)
    assert len(result.code.strip()) > 0, "result.code should be non-empty"


def test_agent_run_returns_review(tmp_working_dir, mock_llm_call, fake_llm_patched):
    cfg = _make_config(tmp_working_dir, "calculator", "write an add function")
    result = CodingAgent(cfg).run()
    assert isinstance(result.review, str)
    assert len(result.review.strip()) > 0, "result.review should be non-empty"


def test_agent_run_output_file_path_matches_project_name(
    tmp_working_dir, mock_llm_call, fake_llm_patched
):
    cfg = _make_config(tmp_working_dir, "my_module", "write a hello function")
    result = CodingAgent(cfg).run()
    assert result.output_file.name == "my_module.py"
    assert result.output_file.parent == tmp_working_dir


def test_agent_run_creates_working_directory_if_missing(
    tmp_path, mock_llm_call, fake_llm_patched
):
    new_dir = tmp_path / "new_subdir" / "nested"
    assert not new_dir.exists()
    cfg = _make_config(new_dir, "calc", "write an add function")
    result = CodingAgent(cfg).run()
    assert new_dir.exists()
    assert result.output_file.exists()
