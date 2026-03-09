"""DeepAgent — public entry point for running a coding task via LangGraph ReAct."""

import logging
from pathlib import Path

from simple_langchain_deepagent.config import DeepAgentConfig
from simple_langchain_deepagent.result import DeepAgentResult
from simple_langchain_deepagent.tools import make_file_tools

logger = logging.getLogger(__name__)

_SUPPORTED_PROVIDERS = ("ollama", "openai", "anthropic")

SYSTEM_PROMPT = (
    "You are a senior software developer. "
    "Implement the requested feature by writing code to files using the available tools. "
    "Think step by step: plan the solution, write the code, then summarise what you did."
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


def create_deep_agent(system_prompt: str, llm, tools):
    """Build a compiled LangGraph ReAct agent graph.

    Args:
        system_prompt: System instructions for the agent.
        llm: A LangChain chat model instance.
        tools: List of LangChain tool objects.

    Returns:
        A compiled LangGraph CompiledGraph ready for invocation.
    """
    from langgraph.prebuilt import create_react_agent

    return create_react_agent(model=llm, tools=tools, prompt=system_prompt)


class DeepAgent:
    """Run a LangGraph ReAct agent for a given coding requirement."""

    def __init__(self, config: DeepAgentConfig) -> None:
        self.config = config

    def run(self) -> DeepAgentResult:
        """Execute the agent graph and return the result."""
        config = self.config
        config.working_directory.mkdir(parents=True, exist_ok=True)

        tools = make_file_tools(config.working_directory)
        llm = _make_llm(config)
        graph = create_deep_agent(SYSTEM_PROMPT, llm, tools)

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

        result = graph.invoke({"messages": [("user", task_prompt)]})

        messages = result.get("messages", [])

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
