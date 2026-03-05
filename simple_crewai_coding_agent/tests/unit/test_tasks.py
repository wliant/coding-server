"""Unit tests for CodingTask and ReviewTask factory functions — no real LLM calls."""


def test_coding_task_output_file(fake_llm, tmp_path):
    from simple_crewai_coding_agent.agents import make_coder_agent
    from simple_crewai_coding_agent.tasks import make_coding_task

    agent = make_coder_agent(llm=fake_llm)
    task = make_coding_task(agent=agent, working_directory=tmp_path, project_name="proj")
    assert task.output_file == str(tmp_path / "proj.py")


def test_coding_task_description_contains_requirement_placeholder(fake_llm, tmp_path):
    from simple_crewai_coding_agent.agents import make_coder_agent
    from simple_crewai_coding_agent.tasks import make_coding_task

    agent = make_coder_agent(llm=fake_llm)
    task = make_coding_task(agent=agent, working_directory=tmp_path, project_name="x")
    assert "{requirement}" in task.description


def test_review_task_context_contains_coding_task(fake_llm, tmp_path):
    from simple_crewai_coding_agent.agents import make_coder_agent, make_reviewer_agent
    from simple_crewai_coding_agent.tasks import make_coding_task, make_review_task

    coder = make_coder_agent(llm=fake_llm)
    reviewer = make_reviewer_agent(llm=fake_llm)
    coding = make_coding_task(agent=coder, working_directory=tmp_path, project_name="x")
    review = make_review_task(agent=reviewer, coding_task=coding)
    assert coding in review.context
