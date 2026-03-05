"""Return type for CodingAgent.run()."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CodingAgentResult:
    """Stable public return type for CodingAgent.run().

    Fields:
        code:        Generated Python source code (content of output file).
        review:      Code review report produced by the reviewer agent.
        output_file: Absolute path to the written source file on disk.
    """

    code: str
    review: str
    output_file: Path
