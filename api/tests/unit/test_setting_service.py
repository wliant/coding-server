"""Unit tests for setting_service."""
import pytest
from fastapi import HTTPException

from api.services import setting_service


async def test_get_settings_returns_defaults_when_empty(db_session):
    """get_settings returns {'agent.work.path': ''} when settings table is empty."""
    result = await setting_service.get_settings(db_session)

    assert result == {"agent.work.path": ""}


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
