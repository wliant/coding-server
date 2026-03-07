import math
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.setting import Setting

ALLOWED_KEYS: set[str] = {
    "agent.work.path",
    "agent.simple_crewai.llm_provider",
    "agent.simple_crewai.llm_model",
    "agent.simple_crewai.llm_temperature",
    "agent.simple_crewai.ollama_base_url",
    "agent.simple_crewai.openai_api_key",
    "agent.simple_crewai.anthropic_api_key",
}

DEFAULTS: dict[str, str] = {
    "agent.work.path": "",
    "agent.simple_crewai.llm_provider": "ollama",
    "agent.simple_crewai.llm_model": "qwen2.5-coder:7b",
    "agent.simple_crewai.llm_temperature": "0.2",
    "agent.simple_crewai.ollama_base_url": "http://localhost:11434",
    "agent.simple_crewai.openai_api_key": "",
    "agent.simple_crewai.anthropic_api_key": "",
}

_VALID_PROVIDERS = {"ollama", "openai", "anthropic"}


def _validate_value(key: str, value: str) -> None:
    """Raise HTTPException 422 if a key-specific validation fails."""
    if key == "agent.simple_crewai.llm_provider":
        if value not in _VALID_PROVIDERS:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid llm_provider: must be one of {', '.join(sorted(_VALID_PROVIDERS))}",
            )
    elif key == "agent.simple_crewai.llm_temperature":
        try:
            temp = float(value)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=422,
                detail="Invalid llm_temperature: must be a number",
            )
        if math.isnan(temp) or not (0.0 <= temp <= 2.0):
            raise HTTPException(
                status_code=422,
                detail="Invalid llm_temperature: must be between 0.0 and 2.0",
            )


async def get_settings(db: AsyncSession) -> dict[str, str]:
    """Return all settings, using defaults for missing keys."""
    result = await db.execute(select(Setting))
    rows = result.scalars().all()
    settings = dict(DEFAULTS)
    for row in rows:
        settings[row.key] = row.value
    return settings


async def upsert_settings(
    db: AsyncSession, updates: dict[str, str]
) -> dict[str, str]:
    """Validate and upsert settings. Raises 422 for unknown keys or invalid values."""
    unknown_keys = set(updates.keys()) - ALLOWED_KEYS
    if unknown_keys:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown setting keys: {', '.join(sorted(unknown_keys))}",
        )

    for key, value in updates.items():
        _validate_value(key, value)

    now = datetime.now(timezone.utc)

    for key, value in updates.items():
        result = await db.execute(select(Setting).where(Setting.key == key))
        existing = result.scalar_one_or_none()

        if existing is None:
            setting = Setting(key=key, value=value, updated_at=now)
            db.add(setting)
        else:
            existing.value = value
            existing.updated_at = now

    await db.commit()
    return await get_settings(db)
