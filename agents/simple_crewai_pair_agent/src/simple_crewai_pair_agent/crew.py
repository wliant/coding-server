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

        logger.info(
            "crew_initializing",
            extra={
                "event": "crew_initializing",
                "working_directory": str(config.working_directory),
                "project_name": config.project_name,
                "llm_provider": config.llm_provider,
                "llm_model": config.llm_model,
                "llm_temperature": config.llm_temperature,
                "ollama_base_url": config.ollama_base_url,
                "openai_api_key_set": bool(
                    config.openai_api_key
                    and config.openai_api_key not in ("", "NA", "PLACEHOLDER")
                ),
                "anthropic_api_key_set": bool(config.anthropic_api_key),
            },
        )

        llm = make_llm(config)
        coder = make_coder_agent(llm=llm)
        reviewer = make_reviewer_agent(llm=llm)

        coding = make_coding_task(
            agent=coder,
            working_directory=config.working_directory,
        )
        review = make_review_task(
            agent=reviewer,
            coding_task=coding,
            working_directory=config.working_directory,
        )

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
            "crew_starting",
            extra={
                "event": "crew_starting",
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
                "crew_failed",
                extra={"event": "crew_failed", "error": str(exc), "project_name": self.config.project_name},
            )
            raise RuntimeError(f"Crew execution failed: {exc}") from exc

        # Find the most recently written .py file in the working directory
        py_files = sorted(
            self.config.working_directory.glob("*.py"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        output_file = py_files[0] if py_files else None
        code = output_file.read_text(encoding="utf-8") if output_file else ""

        review = str(crew_output.raw) if crew_output.raw else ""

        logger.info(
            "crew_completed",
            extra={
                "event": "crew_completed",
                "project_name": self.config.project_name,
                "output_file": str(output_file) if output_file else None,
                "code_length": len(code),
                "elapsed_seconds": round(time.monotonic() - _start, 2),
            },
        )

        return CodingAgentResult(code=code, review=review, output_file=output_file)
