"""simple_crewai_coding_agent — public API."""

from pathlib import Path

from simple_crewai_coding_agent.crew import CodingCrew
from simple_crewai_coding_agent.result import CrewRunResult

__all__ = ["run_crew", "CrewRunResult"]


def run_crew(
    working_directory: str | Path,
    project_name: str,
    requirement: str,
) -> CrewRunResult:
    """Execute the CrewAI coding crew for a given requirement.

    Args:
        working_directory: Path where generated code will be written.
                           Created automatically if it does not exist.
        project_name:      Used as the output filename base (e.g. "calc" → "calc.py").
                           Must be non-empty.
        requirement:       Natural-language description of what code to produce.
                           Must be non-empty after stripping whitespace.

    Returns:
        CrewRunResult with generated code, review report, and output file path.

    Raises:
        ValueError:   If requirement or project_name is empty.
        RuntimeError: If the LLM is unreachable or returns an unrecoverable error.
        OSError:      If working_directory cannot be created or written to.
    """
    if not project_name or not project_name.strip():
        raise ValueError("project_name must be a non-empty string")
    if not requirement or not requirement.strip():
        raise ValueError("requirement must be a non-empty string")

    working_directory = Path(working_directory)
    working_directory.mkdir(parents=True, exist_ok=True)

    crew = CodingCrew(
        working_directory=working_directory,
        project_name=project_name,
        requirement=requirement,
    )
    return crew.run()
