"""Return type for OpenHandsAgent.run()."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OpenHandsAgentResult:
    """Stable public return type for OpenHandsAgent.run().

    Fields:
        code:        Generated source code (content of the last written file, or last AI message).
        summary:     Summary / review produced by the agent.
        output_file: Path to the file written by the agent, or None if no file was found.
    """

    code: str
    summary: str
    output_file: Path | None = None
