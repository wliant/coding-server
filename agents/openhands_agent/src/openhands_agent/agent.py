"""OpenHandsAgent — public entry point for running a coding task via OpenHands SDK."""

import logging
from pathlib import Path

from openhands_agent.config import OpenHandsAgentConfig
from openhands_agent.result import OpenHandsAgentResult

logger = logging.getLogger(__name__)

_SUPPORTED_PROVIDERS = ("ollama", "openai", "anthropic")


class OpenHandsAgent:
    """Run an OpenHands agent for a given coding requirement."""

    def __init__(self, config: OpenHandsAgentConfig) -> None:
        self.config = config

    def run(self) -> OpenHandsAgentResult:
        """Execute the OpenHands agent and return the result."""
        from openhands.sdk import LLM, Agent, LocalConversation

        config = self.config
        config.working_directory.mkdir(parents=True, exist_ok=True)

        llm = self._make_llm()

        logger.info(
            "openhands_agent_invoking",
            extra={
                "event": "openhands_agent_invoking",
                "project_name": config.project_name,
                "llm_provider": config.llm_provider,
                "llm_model": config.llm_model,
            },
        )

        agent = Agent(llm=llm)

        task_prompt = (
            f"Project: {config.project_name}\n\n"
            f"Working directory: {config.working_directory}\n\n"
            f"Requirement:\n{config.requirement}\n\n"
            f"Reminder: create all files using relative paths inside {config.working_directory}."
        )

        conversation = LocalConversation(
            agent=agent,
            workspace=str(config.working_directory),
        )
        try:
            conversation.send_message(task_prompt)
            conversation.run()
        finally:
            conversation.close()

        # Find most recently written file as output_file
        output_file: Path | None = None
        py_files = sorted(
            config.working_directory.rglob("*.py"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if py_files:
            output_file = py_files[0]

        code = output_file.read_text(encoding="utf-8") if output_file else ""
        summary = f"OpenHands agent completed task for project {config.project_name}"

        logger.info(
            "openhands_agent_completed",
            extra={
                "event": "openhands_agent_completed",
                "output_file": str(output_file) if output_file else None,
            },
        )

        return OpenHandsAgentResult(code=code, summary=summary, output_file=output_file)

    def _make_llm(self):
        """Build an openhands.sdk.LLM from the agent config."""
        from openhands.sdk import LLM

        c = self.config
        provider = c.llm_provider

        if provider == "ollama":
            return LLM(
                model=f"ollama/{c.llm_model}",
                base_url=f"{c.ollama_base_url}/v1",
                temperature=c.llm_temperature,
            )

        if provider == "anthropic":
            return LLM(
                model=f"anthropic/{c.llm_model}",
                api_key=c.anthropic_api_key,
                temperature=c.llm_temperature,
            )

        if provider == "openai":
            return LLM(
                model=c.llm_model,
                api_key=c.openai_api_key,
                temperature=c.llm_temperature,
            )

        raise ValueError(
            f"Unknown LLM provider: {provider!r}. "
            f"Supported providers: {', '.join(_SUPPORTED_PROVIDERS)}"
        )
