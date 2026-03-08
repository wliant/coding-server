"""Unit tests for CodingAgent, CodingCrew structure, crewai_agents, and crewai_tasks."""

from unittest.mock import patch

import pytest
from crewai import Process
from crewai_tools import FileReadTool, FileWriterTool

from simple_crewai_pair_agent.config import CodingAgentConfig
from simple_crewai_pair_agent.crewai_agents import make_coder_agent, make_reviewer_agent
from simple_crewai_pair_agent.crewai_tasks import make_coding_task, make_review_task

# ---------------------------------------------------------------------------
# crewai_agents factory functions
# ---------------------------------------------------------------------------


def test_coder_agent_role(fake_llm):
    agent = make_coder_agent(llm=fake_llm)
    assert agent.role == "Senior Python Developer"


def test_coder_agent_no_code_execution(fake_llm):
    agent = make_coder_agent(llm=fake_llm)
    assert agent.allow_code_execution is False


def test_coder_agent_max_retry(fake_llm):
    agent = make_coder_agent(llm=fake_llm)
    assert agent.max_retry_limit == 3


def test_reviewer_agent_role(fake_llm):
    agent = make_reviewer_agent(llm=fake_llm)
    assert agent.role == "Code Reviewer"


def test_reviewer_agent_no_code_execution(fake_llm):
    agent = make_reviewer_agent(llm=fake_llm)
    assert agent.allow_code_execution is False


# ---------------------------------------------------------------------------
# crewai_tasks factory functions
# ---------------------------------------------------------------------------


def test_coding_task_has_file_writer_tool(fake_llm, tmp_path):
    agent = make_coder_agent(llm=fake_llm)
    task = make_coding_task(agent=agent, working_directory=tmp_path)
    tool_types = [type(t) for t in task.tools]
    assert FileWriterTool in tool_types


def test_coding_task_has_file_reader_tool(fake_llm, tmp_path):
    agent = make_coder_agent(llm=fake_llm)
    task = make_coding_task(agent=agent, working_directory=tmp_path)
    tool_types = [type(t) for t in task.tools]
    assert FileReadTool in tool_types


def test_coding_task_no_output_file(fake_llm, tmp_path):
    agent = make_coder_agent(llm=fake_llm)
    task = make_coding_task(agent=agent, working_directory=tmp_path)
    assert not task.output_file


def test_coding_task_description_contains_requirement_placeholder(fake_llm, tmp_path):
    agent = make_coder_agent(llm=fake_llm)
    task = make_coding_task(agent=agent, working_directory=tmp_path)
    assert "{requirement}" in task.description


def test_coding_task_description_contains_working_directory(fake_llm, tmp_path):
    agent = make_coder_agent(llm=fake_llm)
    task = make_coding_task(agent=agent, working_directory=tmp_path)
    assert str(tmp_path) in task.description


def test_coding_task_working_directory_in_description(fake_llm, tmp_path):
    # FileWriterTool no longer accepts directory at construction time;
    # the working directory is communicated to the agent via task description.
    agent = make_coder_agent(llm=fake_llm)
    task = make_coding_task(agent=agent, working_directory=tmp_path)
    assert str(tmp_path) in task.description


def test_review_task_has_file_reader_tool(fake_llm, tmp_path):
    coder = make_coder_agent(llm=fake_llm)
    reviewer = make_reviewer_agent(llm=fake_llm)
    coding = make_coding_task(agent=coder, working_directory=tmp_path)
    review = make_review_task(agent=reviewer, coding_task=coding, working_directory=tmp_path)
    tool_types = [type(t) for t in review.tools]
    assert FileReadTool in tool_types


def test_review_task_context_contains_coding_task(fake_llm, tmp_path):
    coder = make_coder_agent(llm=fake_llm)
    reviewer = make_reviewer_agent(llm=fake_llm)
    coding = make_coding_task(agent=coder, working_directory=tmp_path)
    review = make_review_task(agent=reviewer, coding_task=coding, working_directory=tmp_path)
    assert coding in review.context


# ---------------------------------------------------------------------------
# CodingCrew structure
# ---------------------------------------------------------------------------


@pytest.fixture()
def coding_config(tmp_path) -> CodingAgentConfig:
    return CodingAgentConfig(
        working_directory=tmp_path,
        project_name="proj",
        requirement="write a hello world function",
    )


@pytest.fixture()
def crew_obj(fake_llm, coding_config):
    from simple_crewai_pair_agent.crew import CodingCrew

    with patch("simple_crewai_pair_agent.crew.make_llm", return_value=fake_llm):
        c = CodingCrew(config=coding_config)
    return c


def test_crew_has_two_agents(crew_obj):
    assert len(crew_obj._crew.agents) == 2


def test_crew_process_is_sequential(crew_obj):
    assert crew_obj._crew.process == Process.sequential


def test_crew_has_two_tasks(crew_obj):
    assert len(crew_obj._crew.tasks) == 2


def test_review_task_context_contains_coding_task_in_crew(crew_obj):
    coding_task = crew_obj._crew.tasks[0]
    review_task = crew_obj._crew.tasks[1]
    assert coding_task in review_task.context


def test_crew_init_logs_config(fake_llm, coding_config, caplog):
    """CodingCrew.__init__ emits a structured log with the full config."""
    import logging
    from simple_crewai_pair_agent.crew import CodingCrew

    with patch("simple_crewai_pair_agent.crew.make_llm", return_value=fake_llm):
        with caplog.at_level(logging.INFO, logger="simple_crewai_pair_agent.crew"):
            CodingCrew(config=coding_config)

    assert any("crew_initializing" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# CodingAgent
# ---------------------------------------------------------------------------


def test_coding_agent_sets_openai_env_from_config(tmp_path, monkeypatch):
    """OPENAI_API_KEY is always set from config, not from existing env vars."""
    import os

    from simple_crewai_pair_agent.agent import CodingAgent

    monkeypatch.setenv("OPENAI_API_KEY", "env-key-should-be-overridden")
    cfg = CodingAgentConfig(
        working_directory=tmp_path,
        project_name="p",
        requirement="r",
        openai_api_key="config-key",
    )
    CodingAgent(cfg)

    assert os.environ.get("OPENAI_API_KEY") == "config-key"


def test_coding_agent_uses_placeholder_when_openai_key_empty(tmp_path, monkeypatch):
    """When openai_api_key is empty, OPENAI_API_KEY is set to PLACEHOLDER."""
    import os

    from simple_crewai_pair_agent.agent import CodingAgent

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = CodingAgentConfig(
        working_directory=tmp_path,
        project_name="p",
        requirement="r",
        openai_api_key="",
    )
    CodingAgent(cfg)

    assert os.environ.get("OPENAI_API_KEY") == "PLACEHOLDER"


def test_coding_agent_run_calls_crew(tmp_path, fake_llm, mock_llm_call):
    from simple_crewai_pair_agent.agent import CodingAgent

    cfg = CodingAgentConfig(
        working_directory=tmp_path / "work",
        project_name="myproj",
        requirement="write an add function",
    )
    with patch("simple_crewai_pair_agent.crew.make_llm", return_value=fake_llm):
        agent = CodingAgent(cfg)
        result = agent.run()

    from simple_crewai_pair_agent.result import CodingAgentResult

    assert isinstance(result, CodingAgentResult)
