"""DeepAgent — public entry point for running a coding task via LangChain deepagents."""

import logging
from pathlib import Path

from simple_langchain_deepagent.config import DeepAgentConfig
from simple_langchain_deepagent.result import DeepAgentResult

logger = logging.getLogger(__name__)

_SUPPORTED_PROVIDERS = ("ollama", "openai", "anthropic")

SYSTEM_PROMPT = (
    "You are a senior software developer. "
    "Implement the requested feature by writing code to files using the available tools. "
    "Think step by step: plan the solution, write the code, verify your implementation, "
    "then summarise what you did."
)


def _make_llm(config: DeepAgentConfig):
    """Build a LangChain chat model from a DeepAgentConfig."""
    provider = config.llm_provider
    model = config.llm_model
    temperature = config.llm_temperature

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model,
            base_url=config.ollama_base_url,
            temperature=temperature,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=config.openai_api_key,
            temperature=temperature,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            api_key=config.anthropic_api_key,
            temperature=temperature,
        )

    raise ValueError(
        f"Unknown LLM provider: {provider!r}. "
        f"Supported providers: {', '.join(_SUPPORTED_PROVIDERS)}"
    )


class DeepAgent:
    """Run a LangChain deep agent for a given coding requirement."""

    def __init__(self, config: DeepAgentConfig) -> None:
        self.config = config

    def run(self) -> DeepAgentResult:
        """Execute the deep agent and return the result."""
        from deepagents import create_deep_agent
        from deepagents.backends import LocalShellBackend

        config = self.config
        config.working_directory.mkdir(parents=True, exist_ok=True)

        llm = _make_llm(config)
        backend = LocalShellBackend(root_dir=str(config.working_directory))
        agent = create_deep_agent(
            model=llm,
            backend=backend,
            system_prompt=SYSTEM_PROMPT,
        )

        task_prompt = (
            f"Project: {config.project_name}\n\nRequirement:\n{config.requirement}"
        )

        logger.info(
            "deep_agent_invoking",
            extra={
                "event": "deep_agent_invoking",
                "project_name": config.project_name,
                "llm_provider": config.llm_provider,
                "llm_model": config.llm_model,
            },
        )

        # Stream execution so every agent step is printed to stdout as it happens.
        # stream_mode="values" emits the full state after each node; the last
        # message in the state is the most recent reasoning step / tool call / result.
        state: dict = {}
        seen_ids: set[str] = set()
        for state in agent.stream(
            {"messages": [("user", task_prompt)]},
            stream_mode="values",
        ):
            msgs = state.get("messages", [])
            if msgs:
                last = msgs[-1]
                msg_id = getattr(last, "id", None)
                if msg_id not in seen_ids:
                    seen_ids.add(msg_id)
                    last.pretty_print()

        messages = state.get("messages", [])

        # Extract last AI message as summary
        summary = ""
        for msg in reversed(messages):
            content = getattr(msg, "content", None)
            if content and isinstance(content, str):
                summary = content
                break

        # Find most recently written file as output_file
        output_file: Path | None = None
        py_files = sorted(
            config.working_directory.rglob("*.py"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if py_files:
            output_file = py_files[0]

        code = output_file.read_text(encoding="utf-8") if output_file else summary

        logger.info(
            "deep_agent_completed",
            extra={
                "event": "deep_agent_completed",
                "output_file": str(output_file) if output_file else None,
            },
        )

        return DeepAgentResult(code=code, summary=summary, output_file=output_file)
