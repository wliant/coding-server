"""Unit tests for CoderAgent and ReviewerAgent factory functions — no real LLM calls."""


def test_coder_agent_role(fake_llm):
    from simple_crewai_coding_agent.agents import make_coder_agent

    agent = make_coder_agent(llm=fake_llm)
    assert agent.role == "Senior Python Developer"


def test_coder_agent_no_code_execution(fake_llm):
    from simple_crewai_coding_agent.agents import make_coder_agent

    agent = make_coder_agent(llm=fake_llm)
    assert agent.allow_code_execution is False


def test_coder_agent_max_retry(fake_llm):
    from simple_crewai_coding_agent.agents import make_coder_agent

    agent = make_coder_agent(llm=fake_llm)
    assert agent.max_retry_limit == 3


def test_reviewer_agent_role(fake_llm):
    from simple_crewai_coding_agent.agents import make_reviewer_agent

    agent = make_reviewer_agent(llm=fake_llm)
    assert agent.role == "Code Reviewer"


def test_reviewer_agent_no_code_execution(fake_llm):
    from simple_crewai_coding_agent.agents import make_reviewer_agent

    agent = make_reviewer_agent(llm=fake_llm)
    assert agent.allow_code_execution is False
