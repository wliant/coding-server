from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CrewRunResult:
    """Stable public return type for run_crew().

    Fields:
        code:        Generated Python source code (content of output file).
        review:      Code review report produced by the ReviewerAgent.
        output_file: Absolute path to the written source file on disk.
    """

    code: str
    review: str
    output_file: Path
