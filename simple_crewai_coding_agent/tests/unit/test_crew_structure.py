"""Unit tests for CodingCrew structure — no real LLM calls."""

from unittest.mock import patch

import pytest
from crewai import Process


@pytest.fixture()
def crew_obj(fake_llm, tmp_path):
    from simple_crewai_coding_agent.crew import CodingCrew

    with patch("simple_crewai_coding_agent.crew.make_llm", return_value=fake_llm):
        c = CodingCrew(
            working_directory=tmp_path,
            project_name="proj",
            requirement="write a hello world function",
        )
    return c


def test_crew_has_two_agents(crew_obj):
    assert len(crew_obj._crew.agents) == 2


def test_crew_process_is_sequential(crew_obj):
    assert crew_obj._crew.process == Process.sequential


def test_crew_has_two_tasks(crew_obj):
    assert len(crew_obj._crew.tasks) == 2


def test_review_task_context_contains_coding_task(crew_obj):
    coding_task = crew_obj._crew.tasks[0]
    review_task = crew_obj._crew.tasks[1]
    assert coding_task in review_task.context
