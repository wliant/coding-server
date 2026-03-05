import os

from crewai import LLM

_SUPPORTED_PROVIDERS = ("ollama", "openai", "anthropic")


def make_llm() -> LLM:
    """Build a CrewAI LLM instance from environment variables.

    Defaults to Ollama with qwen2.5-coder:7b when no env vars are set.

    Environment variables:
        LLM_PROVIDER     - Backend: "ollama" (default), "openai", "anthropic"
        LLM_MODEL        - Model name without provider prefix (default: "qwen2.5-coder:7b")
        OLLAMA_BASE_URL  - Ollama endpoint (default: "http://localhost:11434")
        LLM_TEMPERATURE  - Sampling temperature as float string (default: "0.2")
        OPENAI_API_KEY   - Required by CrewAI even for non-OpenAI providers; use "NA" for Ollama

    Raises:
        ValueError: If LLM_PROVIDER is set to an unrecognised value.
    """
    provider = os.getenv("LLM_PROVIDER", "ollama")
    model = os.getenv("LLM_MODEL", "qwen2.5-coder:7b")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    if provider == "ollama":
        # CrewAI validates OPENAI_API_KEY at import time; set a dummy if not already present
        os.environ.setdefault("OPENAI_API_KEY", "NA")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return LLM(
            model=f"ollama/{model}",
            base_url=base_url,
            temperature=temperature,
        )

    if provider == "openai":
        return LLM(
            model=model,
            api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=temperature,
        )

    if provider == "anthropic":
        return LLM(
            model=f"anthropic/{model}",
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            temperature=temperature,
        )

    raise ValueError(
        f"Unknown LLM provider: {provider!r}. "
        f"Supported providers: {', '.join(_SUPPORTED_PROVIDERS)}"
    )
