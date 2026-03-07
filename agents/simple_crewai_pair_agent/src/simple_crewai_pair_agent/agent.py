"""CodingAgent — public entry point for running a coding task."""

import os

from simple_crewai_pair_agent.base import BaseAgent
from simple_crewai_pair_agent.config import CodingAgentConfig
from simple_crewai_pair_agent.crew import CodingCrew
from simple_crewai_pair_agent.result import CodingAgentResult


class CodingAgent(BaseAgent):
    """Run a code-generation + review crew for a given requirement."""

    def __init__(self, config: CodingAgentConfig) -> None:
        super().__init__(config)
        # CrewAI validates OPENAI_API_KEY at import time; always set from config.
        os.environ["OPENAI_API_KEY"] = config.openai_api_key or "PLACEHOLDER"

    def run(self) -> CodingAgentResult:
        """Execute the coding crew and return the result."""
        config: CodingAgentConfig = self.config  # type: ignore[assignment]
        config.working_directory.mkdir(parents=True, exist_ok=True)
        crew = CodingCrew(config=config)
        return crew.run()
