from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.setting import Setting

ALLOWED_KEYS: set[str] = {"agent.work.path"}
DEFAULTS: dict[str, str] = {"agent.work.path": ""}


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
    """Validate and upsert settings. Raises 422 for unknown keys."""
    unknown_keys = set(updates.keys()) - ALLOWED_KEYS
    if unknown_keys:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown setting keys: {', '.join(sorted(unknown_keys))}",
        )

    now = datetime.now(timezone.utc)

    for key, value in updates.items():
        # Try to find existing row
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
