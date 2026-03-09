import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from api.schemas.agent import AgentSummary


class TaskStatus(str, Enum):
    pending = "pending"
    aborted = "aborted"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    cleaning_up = "cleaning_up"
    cleaned = "cleaned"


class ProjectType(str, Enum):
    new = "new"
    existing = "existing"


class ProjectSummary(BaseModel):
    id: uuid.UUID
    name: str | None = None
    source_type: str
    git_url: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProjectSummaryWithGitUrl(BaseModel):
    id: uuid.UUID
    name: str | None = None
    source_type: str
    git_url: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: uuid.UUID
    project: ProjectSummary
    agent: AgentSummary | None = None
    requirements: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None

    model_config = {"from_attributes": True}


class TaskDetailResponse(BaseModel):
    id: uuid.UUID
    project: ProjectSummaryWithGitUrl
    agent: AgentSummary | None = None
    requirements: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    work_directory_path: str | None = None
    elapsed_seconds: int | None = None
    branch: str | None = None
    assigned_worker_id: str | None = None
    assigned_worker_url: str | None = None

    model_config = {"from_attributes": True}


class CleanupResponse(BaseModel):
    task_id: uuid.UUID
    status: str = "cleaning_up"


class WorkerStatus(BaseModel):
    worker_id: str
    agent_type: str
    worker_url: str
    status: str
    current_task_id: str | None = None
    registered_at: datetime
    last_heartbeat_at: datetime


class PushResponse(BaseModel):
    branch_name: str
    remote_url: str
    pushed_at: datetime


class PushTaskRequest(BaseModel):
    git_url: str | None = None


class CreateTaskRequest(BaseModel):
    project_type: ProjectType
    project_name: str | None = None
    agent_id: uuid.UUID
    git_url: str | None = None
    branch: str | None = None
    requirements: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_cross_fields(self) -> "CreateTaskRequest":
        if self.project_type == ProjectType.new:
            if not self.project_name or not self.project_name.strip():
                raise ValueError("project_name is required when project_type is 'new'")
        if self.project_type == ProjectType.existing:
            if not self.git_url or not self.git_url.strip():
                raise ValueError("git_url is required when project_type is 'existing'")
        return self


class UpdateTaskRequest(BaseModel):
    status: TaskStatus | None = None
    project_id: uuid.UUID | None = None
    requirements: str | None = Field(default=None, min_length=1)
