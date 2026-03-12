from datetime import datetime

from pydantic import BaseModel


class SandboxStatus(BaseModel):
    sandbox_id: str
    sandbox_url: str
    status: str
    labels: list[str] = []
    registered_at: datetime
    last_heartbeat_at: datetime
