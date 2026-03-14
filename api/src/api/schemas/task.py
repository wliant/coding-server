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


class TaskType(str, Enum):
    build_feature = "build_feature"
    fix_bug = "fix_bug"
    review_code = "review_code"
    refactor_code = "refactor_code"
    write_tests = "write_tests"
    scaffold_project = "scaffold_project"


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
    task_type: str
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
    task_type: str
    commits_to_review: int | None = None
    required_capabilities: list[str] | None = None
    assigned_sandbox_id: str | None = None
    assigned_sandbox_url: str | None = None

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
    task_type: TaskType
    project_name: str | None = None
    agent_id: uuid.UUID
    git_url: str | None = None
    branch: str | None = None
    requirements: str = Field(..., min_length=1)
    commits_to_review: int | None = None
    required_capabilities: list[str] | None = None

    @model_validator(mode="after")
    def validate_cross_fields(self) -> "CreateTaskRequest":
        if self.task_type == TaskType.scaffold_project:
            if not self.project_name or not self.project_name.strip():
                raise ValueError("project_name is required for scaffold_project tasks")
        else:
            if not self.git_url or not self.git_url.strip():
                raise ValueError("git_url is required for non-scaffold tasks")
        if self.task_type == TaskType.review_code:
            if not self.branch or not self.branch.strip():
                raise ValueError("branch is required for review_code tasks")
        if self.commits_to_review is not None and self.task_type != TaskType.review_code:
            raise ValueError("commits_to_review is only valid for review_code tasks")
        return self


class UpdateTaskRequest(BaseModel):
    status: TaskStatus | None = None
    project_id: uuid.UUID | None = None
    requirements: str | None = Field(default=None, min_length=1)
