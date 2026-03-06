import uuid
from datetime import datetime

from pydantic import BaseModel


class AgentSummary(BaseModel):
    id: uuid.UUID
    identifier: str
    display_name: str

    model_config = {"from_attributes": True}


class AgentResponse(BaseModel):
    id: uuid.UUID
    identifier: str
    display_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
