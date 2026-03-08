"""Integration-level fixtures for test_crew_kickoff.py."""

import pytest

from simple_crewai_pair_agent.crew import CodingCrew
from simple_crewai_pair_agent.result import CodingAgentResult


@pytest.fixture()
def fake_crew_run(mocker):
    """Patch CodingCrew.run to write a fake .py file and return a valid CodingAgentResult.

    This avoids the need for a real (or realistically mocked) LLM that issues tool calls.
    The mocked LLM patches in mock_llm_call return plain text which CrewAI treats as a
    final answer — no tool calls are triggered, so FileWriterTool never runs and
    working_directory stays empty.  Patching CodingCrew.run directly lets us test the
    CodingAgent / result plumbing without depending on CrewAI's internal tool-call logic.
    """

    def _run(self: CodingCrew) -> CodingAgentResult:
        self.config.working_directory.mkdir(parents=True, exist_ok=True)
        out = self.config.working_directory / "solution.py"
        code = "def placeholder():\n    pass\n"
        out.write_text(code, encoding="utf-8")
        return CodingAgentResult(
            code=code,
            review="Code looks good.",
            output_file=out,
        )

    mocker.patch.object(CodingCrew, "run", _run)
