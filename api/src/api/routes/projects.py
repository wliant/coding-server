from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.schemas.task import ProjectSummary
from api.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectSummary])
async def list_projects(db: AsyncSession = Depends(get_db)):
    projects = await project_service.list_named_projects(db)
    return [ProjectSummary.model_validate(p) for p in projects]
