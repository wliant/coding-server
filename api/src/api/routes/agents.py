from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.models.agent import Agent
from api.schemas.agent import AgentResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Agent).where(Agent.is_active == True).order_by(Agent.display_name)  # noqa: E712
    )
    return [AgentResponse.model_validate(a) for a in result.scalars().all()]
