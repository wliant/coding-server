"""Unit tests for CodingAgentConfig and make_llm(config)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from simple_crewai_pair_agent.config import CodingAgentConfig
from simple_crewai_pair_agent.llm import make_llm

# ---------------------------------------------------------------------------
# CodingAgentConfig — defaults
# ---------------------------------------------------------------------------


def test_defaults() -> None:
    cfg = CodingAgentConfig(
        working_directory=Path("/tmp/x"),
        project_name="hello",
        requirement="write a hello function",
    )
    assert cfg.llm_provider == "ollama"
    assert cfg.llm_model == "qwen2.5-coder:7b"
    assert cfg.llm_temperature == 0.2
    assert cfg.ollama_base_url == "http://localhost:11434"
    assert cfg.openai_api_key == "NA"
    assert cfg.anthropic_api_key == ""


def test_frozen_raises_on_mutation() -> None:
    cfg = CodingAgentConfig(
        working_directory=Path("/tmp/x"),
        project_name="hello",
        requirement="write something",
    )
    with pytest.raises(ValidationError):
        cfg.llm_model = "other"  # type: ignore[misc]


def test_project_name_empty_raises() -> None:
    with pytest.raises(ValidationError):
        CodingAgentConfig(
            working_directory=Path("/tmp/x"),
            project_name="",
            requirement="write something",
        )


def test_requirement_empty_raises() -> None:
    with pytest.raises(ValidationError):
        CodingAgentConfig(
            working_directory=Path("/tmp/x"),
            project_name="proj",
            requirement="",
        )


def test_temperature_out_of_range_raises() -> None:
    with pytest.raises(ValidationError):
        CodingAgentConfig(
            working_directory=Path("/tmp/x"),
            project_name="proj",
            requirement="req",
            llm_temperature=3.0,
        )


# ---------------------------------------------------------------------------
# make_llm — config-driven provider branching
# ---------------------------------------------------------------------------


def test_ollama_model_includes_prefix() -> None:
    cfg = CodingAgentConfig(
        working_directory=Path("/tmp/x"),
        project_name="p",
        requirement="r",
        llm_provider="ollama",
        llm_model="qwen2.5-coder:7b",
    )
    llm = make_llm(cfg)
    assert llm.model == "ollama/qwen2.5-coder:7b"


def test_ollama_base_url_is_forwarded() -> None:
    custom_url = "http://my-ollama-server:11434"
    cfg = CodingAgentConfig(
        working_directory=Path("/tmp/x"),
        project_name="p",
        requirement="r",
        llm_provider="ollama",
        ollama_base_url=custom_url,
    )
    llm = make_llm(cfg)
    assert llm.base_url == custom_url


def test_openai_provider_no_prefix() -> None:
    cfg = CodingAgentConfig(
        working_directory=Path("/tmp/x"),
        project_name="p",
        requirement="r",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        openai_api_key="sk-test",
    )
    llm = make_llm(cfg)
    assert llm.model == "gpt-4o-mini"


def test_anthropic_provider_model_contains_name() -> None:
    import os
    from unittest.mock import patch

    cfg = CodingAgentConfig(
        working_directory=Path("/tmp/x"),
        project_name="p",
        requirement="r",
        llm_provider="anthropic",
        llm_model="claude-haiku-4-5-20251001",
        anthropic_api_key="sk-ant-test",
    )
    # CrewAI's native Anthropic provider validates the key via env var at instantiation time
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
        llm = make_llm(cfg)
    assert "claude-haiku-4-5-20251001" in llm.model


def test_unknown_provider_raises_value_error() -> None:
    cfg = CodingAgentConfig(
        working_directory=Path("/tmp/x"),
        project_name="p",
        requirement="r",
        llm_provider="unknown-provider",
    )
    with pytest.raises(ValueError, match="unknown"):
        make_llm(cfg)
