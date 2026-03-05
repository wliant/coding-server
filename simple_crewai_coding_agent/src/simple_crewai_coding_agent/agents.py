"""Agent factory functions for the CrewAI coding crew."""
from crewai import LLM, Agent


def make_coder_agent(llm: LLM) -> Agent:
    """Create the Coder agent responsible for writing Python source code."""
    return Agent(
        role="Senior Python Developer",
        goal=(
            "Write clean, functional, well-commented Python code that fulfills"
            " the given requirement"
        ),
        backstory=(
            "You are an experienced Python developer with 10 years of expertise writing "
            "clean, maintainable code. You focus on correctness, readability, and Pythonic style."
        ),
        llm=llm,
        allow_code_execution=False,
        max_retry_limit=3,
        verbose=False,
    )


def make_reviewer_agent(llm: LLM) -> Agent:
    """Create the Reviewer agent responsible for reviewing generated code."""
    return Agent(
        role="Code Reviewer",
        goal=(
            "Review Python code for correctness, clarity, edge cases,"
            " and adherence to the requirement"
        ),
        backstory=(
            "You are a senior engineer specialising in Python code quality and best practices. "
            "You provide clear, actionable feedback on code correctness, style, and completeness."
        ),
        llm=llm,
        allow_code_execution=False,
        max_retry_limit=3,
        verbose=False,
    )
