"""Unit tests for make_llm() — verifies provider branching from env vars."""

import os
from unittest.mock import patch

import pytest


def test_default_provider_is_ollama():
    """No env vars set → defaults to ollama with qwen2.5-coder:7b."""
    env = {"LLM_PROVIDER": "", "LLM_MODEL": "", "OPENAI_API_KEY": "NA"}
    with patch.dict(os.environ, env, clear=False):
        # Remove provider/model keys so defaults kick in
        os.environ.pop("LLM_PROVIDER", None)
        os.environ.pop("LLM_MODEL", None)
        from simple_crewai_coding_agent.config import make_llm

        llm = make_llm()
    assert llm.model.startswith("ollama/")
    assert "qwen2.5-coder:7b" in llm.model


def test_ollama_provider_model_includes_prefix():
    with patch.dict(
        os.environ,
        {"LLM_PROVIDER": "ollama", "LLM_MODEL": "qwen2.5-coder:7b", "OPENAI_API_KEY": "NA"},
    ):
        from simple_crewai_coding_agent.config import make_llm

        llm = make_llm()
    assert llm.model == "ollama/qwen2.5-coder:7b"


def test_ollama_base_url_is_configurable():
    custom_url = "http://my-ollama-server:11434"
    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": custom_url,
            "OPENAI_API_KEY": "NA",
        },
    ):
        from simple_crewai_coding_agent.config import make_llm

        llm = make_llm()
    assert llm.base_url == custom_url


def test_openai_provider_no_prefix():
    with patch.dict(
        os.environ,
        {"LLM_PROVIDER": "openai", "LLM_MODEL": "gpt-4o-mini", "OPENAI_API_KEY": "sk-test"},
    ):
        from simple_crewai_coding_agent.config import make_llm

        llm = make_llm()
    assert llm.model == "gpt-4o-mini"


def test_anthropic_provider_model_contains_name():
    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "anthropic",
            "LLM_MODEL": "claude-haiku-4-5-20251001",
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "OPENAI_API_KEY": "NA",
        },
    ):
        from simple_crewai_coding_agent.config import make_llm

        llm = make_llm()
    # CrewAI's native Anthropic provider normalises the model name (strips prefix)
    assert "claude-haiku-4-5-20251001" in llm.model


def test_unknown_provider_raises_value_error():
    with patch.dict(os.environ, {"LLM_PROVIDER": "unknown-provider", "OPENAI_API_KEY": "NA"}):
        from simple_crewai_coding_agent.config import make_llm

        with pytest.raises(ValueError, match="unknown"):
            make_llm()


def test_invalid_temperature_raises_clear_value_error():
    with patch.dict(
        os.environ, {"LLM_TEMPERATURE": "not-a-float", "OPENAI_API_KEY": "NA"}
    ):
        from simple_crewai_coding_agent.config import make_llm

        with pytest.raises(ValueError, match="LLM_TEMPERATURE"):
            make_llm()
