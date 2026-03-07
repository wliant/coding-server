"""Unit tests for setting_service."""
import pytest
from fastapi import HTTPException

from api.services import setting_service

ALL_DEFAULTS = {
    "agent.work.path": "",
    "agent.simple_crewai.llm_provider": "ollama",
    "agent.simple_crewai.llm_model": "qwen2.5-coder:7b",
    "agent.simple_crewai.llm_temperature": "0.2",
    "agent.simple_crewai.ollama_base_url": "http://localhost:11434",
    "agent.simple_crewai.openai_api_key": "",
    "agent.simple_crewai.anthropic_api_key": "",
}


async def test_get_settings_returns_defaults_when_empty(db_session):
    """get_settings returns all 7 defaults when settings table is empty."""
    result = await setting_service.get_settings(db_session)

    assert result == ALL_DEFAULTS


async def test_get_settings_returns_persisted_value(db_session):
    """get_settings returns the stored value when a row exists."""
    await setting_service.upsert_settings(
        db_session, {"agent.work.path": "/home/user/work"}
    )

    result = await setting_service.get_settings(db_session)
    assert result["agent.work.path"] == "/home/user/work"


async def test_upsert_settings_inserts_on_first_call(db_session):
    """upsert_settings inserts a new row on first call."""
    result = await setting_service.upsert_settings(
        db_session, {"agent.work.path": "/tmp"}
    )

    assert result["agent.work.path"] == "/tmp"


async def test_upsert_settings_updates_on_subsequent_call(db_session):
    """upsert_settings updates the existing row on subsequent calls."""
    await setting_service.upsert_settings(db_session, {"agent.work.path": "/tmp"})
    result = await setting_service.upsert_settings(
        db_session, {"agent.work.path": "/var/work"}
    )

    assert result["agent.work.path"] == "/var/work"


async def test_upsert_settings_unknown_key_raises_422(db_session):
    """upsert_settings raises 422 for unknown keys."""
    with pytest.raises(HTTPException) as exc_info:
        await setting_service.upsert_settings(
            db_session, {"unknown.key": "value"}
        )

    assert exc_info.value.status_code == 422


# --- New agent settings keys ---

async def test_upsert_all_six_agent_keys_accepted(db_session):
    """All 6 simple_crewai keys are accepted and persisted."""
    updates = {
        "agent.simple_crewai.llm_provider": "openai",
        "agent.simple_crewai.llm_model": "gpt-4o",
        "agent.simple_crewai.llm_temperature": "0.7",
        "agent.simple_crewai.ollama_base_url": "http://my-ollama:11434",
        "agent.simple_crewai.openai_api_key": "sk-test",
        "agent.simple_crewai.anthropic_api_key": "ant-test",
    }
    result = await setting_service.upsert_settings(db_session, updates)

    assert result["agent.simple_crewai.llm_provider"] == "openai"
    assert result["agent.simple_crewai.llm_model"] == "gpt-4o"
    assert result["agent.simple_crewai.llm_temperature"] == "0.7"
    assert result["agent.simple_crewai.ollama_base_url"] == "http://my-ollama:11434"
    assert result["agent.simple_crewai.openai_api_key"] == "sk-test"
    assert result["agent.simple_crewai.anthropic_api_key"] == "ant-test"


async def test_get_settings_returns_all_seven_keys_with_defaults(db_session):
    """get_settings always returns all 7 keys including 6 new agent keys."""
    result = await setting_service.get_settings(db_session)

    assert set(result.keys()) == set(ALL_DEFAULTS.keys())
    assert result["agent.simple_crewai.llm_provider"] == "ollama"
    assert result["agent.simple_crewai.llm_model"] == "qwen2.5-coder:7b"
    assert result["agent.simple_crewai.llm_temperature"] == "0.2"
    assert result["agent.simple_crewai.ollama_base_url"] == "http://localhost:11434"
    assert result["agent.simple_crewai.openai_api_key"] == ""
    assert result["agent.simple_crewai.anthropic_api_key"] == ""


async def test_upsert_llm_provider_invalid_value_raises_422(db_session):
    """upsert_settings raises 422 when llm_provider is not a supported value."""
    with pytest.raises(HTTPException) as exc_info:
        await setting_service.upsert_settings(
            db_session, {"agent.simple_crewai.llm_provider": "mistral"}
        )

    assert exc_info.value.status_code == 422


async def test_upsert_llm_provider_valid_values_accepted(db_session):
    """All three valid provider values are accepted."""
    for provider in ("ollama", "openai", "anthropic"):
        result = await setting_service.upsert_settings(
            db_session, {"agent.simple_crewai.llm_provider": provider}
        )
        assert result["agent.simple_crewai.llm_provider"] == provider


async def test_upsert_llm_temperature_non_numeric_raises_422(db_session):
    """upsert_settings raises 422 when llm_temperature is not a number."""
    with pytest.raises(HTTPException) as exc_info:
        await setting_service.upsert_settings(
            db_session, {"agent.simple_crewai.llm_temperature": "hot"}
        )

    assert exc_info.value.status_code == 422


async def test_upsert_llm_temperature_below_range_raises_422(db_session):
    """upsert_settings raises 422 when llm_temperature is below 0.0."""
    with pytest.raises(HTTPException) as exc_info:
        await setting_service.upsert_settings(
            db_session, {"agent.simple_crewai.llm_temperature": "-0.1"}
        )

    assert exc_info.value.status_code == 422


async def test_upsert_llm_temperature_above_range_raises_422(db_session):
    """upsert_settings raises 422 when llm_temperature is above 2.0."""
    with pytest.raises(HTTPException) as exc_info:
        await setting_service.upsert_settings(
            db_session, {"agent.simple_crewai.llm_temperature": "2.001"}
        )

    assert exc_info.value.status_code == 422


async def test_upsert_llm_temperature_boundary_values_accepted(db_session):
    """Temperature boundary values 0.0 and 2.0 are accepted."""
    for temp in ("0.0", "2.0"):
        result = await setting_service.upsert_settings(
            db_session, {"agent.simple_crewai.llm_temperature": temp}
        )
        assert result["agent.simple_crewai.llm_temperature"] == temp


async def test_upsert_llm_temperature_nan_raises_422(db_session):
    """upsert_settings raises 422 when llm_temperature is 'nan'."""
    with pytest.raises(HTTPException) as exc_info:
        await setting_service.upsert_settings(
            db_session, {"agent.simple_crewai.llm_temperature": "nan"}
        )

    assert exc_info.value.status_code == 422


async def test_upsert_llm_temperature_empty_raises_422(db_session):
    """upsert_settings raises 422 when llm_temperature is empty string."""
    with pytest.raises(HTTPException) as exc_info:
        await setting_service.upsert_settings(
            db_session, {"agent.simple_crewai.llm_temperature": ""}
        )

    assert exc_info.value.status_code == 422
