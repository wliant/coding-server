"""Task factory functions for the CrewAI coding crew."""

from pathlib import Path

from crewai import Agent, Task
from crewai_tools import FileReadTool, FileWriterTool


def make_coding_task(agent: Agent, working_directory: Path) -> Task:
    """Create the coding task assigned to the Coder agent.

    The agent writes its Python implementation to working_directory using
    FileWriterTool and may read it back with FileReaderTool. No output_file
    is used; all file I/O goes through the configured tools.
    """
    writer = FileWriterTool(directory=str(working_directory))
    reader = FileReadTool(directory=str(working_directory))
    return Task(
        description=(
            "Implement the following requirement in Python:\n\n"
            "{requirement}\n\n"
            "Write a complete, runnable Python module with clear inline comments. "
            "Include all necessary imports. Do not include markdown code fences — "
            "output only valid Python source code.\n"
            f"Use the file writer tool to save your code to the working directory: {working_directory}\n"
            "Choose a short, descriptive filename such as solution.py.\n"
            "Your final response MUST state the exact filename you used."
        ),
        expected_output=(
            "The exact filename written (e.g. solution.py) followed by a one-line "
            "summary of what the module implements."
        ),
        agent=agent,
        tools=[writer, reader],
    )


def make_review_task(agent: Agent, coding_task: Task, working_directory: Path) -> Task:
    """Create the review task assigned to the Reviewer agent.

    The agent uses FileReaderTool to read the file written by the Coder
    (filename is in the Coder's output via context), then produces a review.
    """
    reader = FileReadTool(directory=str(working_directory))
    return Task(
        description=(
            "The Coder agent has written a Python implementation to the working "
            f"directory ({working_directory}). The exact filename is stated in the "
            "Coder's output. Use the file reader tool to read that file, then review "
            "the code. Check for: correctness, edge cases, code clarity, Pythonic "
            "style, and adherence to the original requirement. "
            "Summarise your findings and list any recommended improvements."
        ),
        expected_output=(
            "A concise code review report summarising the implementation quality, "
            "listing any issues found, and providing specific improvement recommendations."
        ),
        agent=agent,
        context=[coding_task],
        tools=[reader],
    )
