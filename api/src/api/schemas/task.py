import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    pending = "pending"
    aborted = "aborted"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class DevAgentType(str, Enum):
    spec_driven_development = "spec_driven_development"


class TestAgentType(str, Enum):
    generic_testing = "generic_testing"


class ProjectType(str, Enum):
    new = "new"
    existing = "existing"


class ProjectSummary(BaseModel):
    id: uuid.UUID
    name: str | None
    source_type: str

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: uuid.UUID
    project: ProjectSummary
    dev_agent_type: DevAgentType
    test_agent_type: TestAgentType
    requirements: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None

    model_config = {"from_attributes": True}


class CreateTaskRequest(BaseModel):
    project_type: ProjectType
    project_id: uuid.UUID | None = None
    dev_agent_type: DevAgentType
    test_agent_type: TestAgentType
    requirements: str = Field(..., min_length=1)


class UpdateTaskRequest(BaseModel):
    status: TaskStatus | None = None
    project_id: uuid.UUID | None = None
    dev_agent_type: DevAgentType | None = None
    test_agent_type: TestAgentType | None = None
    requirements: str | None = Field(default=None, min_length=1)
