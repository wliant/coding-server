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


class ProjectSummaryWithGitUrl(BaseModel):
    id: uuid.UUID
    name: str | None = None
    source_type: str
    git_url: str | None = None

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


class TaskDetailResponse(BaseModel):
    id: uuid.UUID
    project: ProjectSummaryWithGitUrl
    dev_agent_type: DevAgentType
    test_agent_type: TestAgentType
    requirements: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    work_directory_path: str | None = None
    elapsed_seconds: int | None = None

    model_config = {"from_attributes": True}


class PushResponse(BaseModel):
    branch_name: str
    remote_url: str
    pushed_at: datetime


class CreateTaskRequest(BaseModel):
    project_type: ProjectType
    project_id: uuid.UUID | None = None
    dev_agent_type: DevAgentType
    test_agent_type: TestAgentType
    requirements: str = Field(..., min_length=1)
    git_url: str | None = None


class UpdateTaskRequest(BaseModel):
    status: TaskStatus | None = None
    project_id: uuid.UUID | None = None
    dev_agent_type: DevAgentType | None = None
    test_agent_type: TestAgentType | None = None
    requirements: str | None = Field(default=None, min_length=1)
