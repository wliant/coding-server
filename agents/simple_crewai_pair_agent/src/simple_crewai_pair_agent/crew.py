"""CodingCrew — internal orchestrator for the coding agent."""

import logging
import time

from crewai import Crew, Process

from simple_crewai_pair_agent.config import CodingAgentConfig
from simple_crewai_pair_agent.crewai_agents import make_coder_agent, make_reviewer_agent
from simple_crewai_pair_agent.crewai_tasks import make_coding_task, make_review_task
from simple_crewai_pair_agent.llm import make_llm
from simple_crewai_pair_agent.result import CodingAgentResult

logger = logging.getLogger(__name__)


class CodingCrew:
    """Assembles and runs a two-agent CrewAI crew (Coder + Reviewer)."""

    def __init__(self, config: CodingAgentConfig) -> None:
        self.config = config

        llm = make_llm(config)
        coder = make_coder_agent(llm=llm)
        reviewer = make_reviewer_agent(llm=llm)

        coding = make_coding_task(
            agent=coder,
            working_directory=config.working_directory,
            project_name=config.project_name,
        )
        review = make_review_task(agent=reviewer, coding_task=coding)

        self._crew = Crew(
            agents=[coder, reviewer],
            tasks=[coding, review],
            process=Process.sequential,
            verbose=False,
        )

    def run(self) -> CodingAgentResult:
        """Execute the crew and return a CodingAgentResult.

        Raises:
            RuntimeError: If the crew fails due to an LLM or execution error.
        """
        logger.info(
            "crew starting",
            extra={
                "project_name": self.config.project_name,
                "working_directory": str(self.config.working_directory),
            },
        )
        _start = time.monotonic()
        try:
            crew_output = self._crew.kickoff(inputs={"requirement": self.config.requirement})
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            logger.error(
                "crew failed",
                extra={"error": str(exc), "project_name": self.config.project_name},
            )
            raise RuntimeError(f"Crew execution failed: {exc}") from exc

        output_file = self.config.working_directory / f"{self.config.project_name}.py"

        # Read the generated code from disk (written by CrewAI via output_file)
        code = output_file.read_text(encoding="utf-8") if output_file.exists() else ""

        # The final task output (review report) is in crew_output.raw
        review = str(crew_output.raw) if crew_output.raw else ""

        logger.info(
            "crew completed",
            extra={
                "project_name": self.config.project_name,
                "output_file": str(output_file),
                "code_length": len(code),
                "elapsed_seconds": round(time.monotonic() - _start, 2),
            },
        )

        return CodingAgentResult(code=code, review=review, output_file=output_file)
