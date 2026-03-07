"""Config-driven LLM factory — no env var reads."""

from crewai import LLM

from simple_crewai_pair_agent.config import CodingAgentConfig

_SUPPORTED_PROVIDERS = ("ollama", "openai", "anthropic")


def make_llm(config: CodingAgentConfig) -> LLM:
    """Build a CrewAI LLM instance from a CodingAgentConfig.

    Raises:
        ValueError: If config.llm_provider is not a recognised value.
    """
    provider = config.llm_provider
    model = config.llm_model
    temperature = config.llm_temperature

    if provider == "ollama":
        return LLM(
            model=f"ollama/{model}",
            base_url=config.ollama_base_url,
            temperature=temperature,
            timeout=1800,  # 30 minutes — large local models can be slow
            num_ctx=16384,  # limit context window to avoid slow KV-cache on large models
        )

    if provider == "openai":
        return LLM(
            model=model,
            api_key=config.openai_api_key,
            temperature=temperature,
        )

    if provider == "anthropic":
        return LLM(
            model=f"anthropic/{model}",
            api_key=config.anthropic_api_key,
            temperature=temperature,
        )

    raise ValueError(
        f"Unknown LLM provider: {provider!r}. "
        f"Supported providers: {', '.join(_SUPPORTED_PROVIDERS)}"
    )
