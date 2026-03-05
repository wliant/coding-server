from pathlib import Path

from crewai import Agent, Task


def make_coding_task(agent: Agent, working_directory: Path, project_name: str) -> Task:
    """Create the coding task assigned to the Coder agent.

    The task output is written directly to {working_directory}/{project_name}.py
    via CrewAI's output_file parameter.
    """
    output_file = str(working_directory / f"{project_name}.py")
    return Task(
        description=(
            "Implement the following requirement in Python:\n\n"
            "{requirement}\n\n"
            "Write a complete, runnable Python module with clear inline comments. "
            "Include all necessary imports. Do not include markdown code fences — "
            "output only valid Python source code."
        ),
        expected_output=(
            "A complete Python module that implements the requirement, "
            "with inline comments explaining the logic."
        ),
        agent=agent,
        output_file=output_file,
    )


def make_review_task(agent: Agent, coding_task: Task) -> Task:
    """Create the review task assigned to the Reviewer agent.

    Receives the Coder's output automatically via the context parameter.
    """
    return Task(
        description=(
            "Review the Python implementation produced by the Coder agent. "
            "Check for: correctness, edge cases, code clarity, Pythonic style, "
            "and adherence to the original requirement. "
            "Summarise your findings and list any recommended improvements."
        ),
        expected_output=(
            "A concise code review report summarising the implementation quality, "
            "listing any issues found, and providing specific improvement recommendations."
        ),
        agent=agent,
        context=[coding_task],
    )
