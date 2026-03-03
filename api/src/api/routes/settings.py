from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.schemas.setting import SettingsResponse, UpdateSettingsRequest
from api.services import setting_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    settings = await setting_service.get_settings(db)
    return SettingsResponse(settings=settings)


@router.put("", response_model=SettingsResponse)
async def update_settings(
    req: UpdateSettingsRequest, db: AsyncSession = Depends(get_db)
):
    settings = await setting_service.upsert_settings(db, req.settings)
    return SettingsResponse(settings=settings)
