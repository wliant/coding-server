# Task Lifecycle
Last updated: 2026-03-14

## Overview

Everything about how a coding task moves through the system: submission, execution, completion, push, and cleanup. Tasks are the primary unit of work in the coding-machine system. A user submits a natural-language coding requirement, the system executes it via an LLM-powered agent, and the resulting code can be pushed to a Git repository.

## Domain Concepts

### Task Statuses

| Status | Description | Transitions To |
|--------|-------------|---------------|
| `pending` | Submitted, waiting for a worker | `in_progress`, `aborted` |
| `in_progress` | Delegated to a worker, agent executing | `completed`, `failed` |
| `completed` | Agent finished successfully | `cleaning_up` |
| `failed` | Agent encountered an error | `cleaning_up` |
| `aborted` | User cancelled before execution began | `pending` (via resubmit) |
| `cleaning_up` | Cleanup initiated, controller freeing worker | `cleaned` |
| `cleaned` | Cleanup complete, terminal state | — |

### Task Types

| Value | Label | Requirements |
|-------|-------|-------------|
| `build_feature` | Build a Feature | `git_url` required |
| `fix_bug` | Fix a Bug | `git_url` required |
| `review_code` | Review Code | `git_url` required, `branch` required, optional `commits_to_review` |
| `refactor_code` | Refactor Code | `git_url` required |
| `write_tests` | Write Tests | `git_url` required |
| `scaffold_project` | Scaffold a Project | `project_name` required, `git_url` optional |

### Cross-Field Validation Rules

- `scaffold_project` tasks require `project_name`; `git_url` is optional
- All non-scaffold types require `git_url`
- `review_code` requires `branch`
- `commits_to_review` is only valid for `review_code` (422 if set on other types)

## Data Model

### `jobs` table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | |
| project_id | UUID | FK → projects.id, NOT NULL | |
| requirement | TEXT | NOT NULL | Natural-language task description |
| status | VARCHAR(20) | NOT NULL, default "pending" | See task statuses above |
| task_type | VARCHAR(30) | NOT NULL, default "build_feature" | See task types above |
| agent_id | UUID | FK → agents.id, nullable | Selected agent from registry |
| branch | VARCHAR(255) | nullable | Git branch to clone/checkout |
| commits_to_review | INTEGER | nullable | For review_code tasks only |
| assigned_worker_id | VARCHAR(36) | nullable | Worker ID assigned by controller |
| assigned_worker_url | TEXT | nullable | Worker URL for direct file browsing |
| lease_holder | VARCHAR(36) | nullable | Worker UUID holding the lease |
| lease_expires_at | TIMESTAMPTZ | nullable | Lease TTL expiry timestamp |
| required_capabilities | TEXT[] | nullable | Capability strings required for this task |
| assigned_sandbox_id | VARCHAR(255) | nullable | Sandbox allocated by controller |
| assigned_sandbox_url | TEXT | nullable | Sandbox URL for file/MCP access |
| error_message | TEXT | nullable | Human-readable error for failed jobs |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | |
| started_at | TIMESTAMPTZ | nullable | When worker began execution |
| completed_at | TIMESTAMPTZ | nullable | When execution finished |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() | |

### `work_directories` table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | |
| job_id | UUID | FK → jobs.id, UNIQUE, NOT NULL | One work directory per job |
| path | TEXT | UNIQUE, NOT NULL | Filesystem path |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | |

## API Contracts

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks` | List all tasks (joined with project + agent), newest first |
| POST | `/tasks` | Create a new task |
| GET | `/tasks/{id}` | Task detail (includes work directory, elapsed time, worker URL) |
| PATCH | `/tasks/{id}` | Abort or resubmit a task |
| POST | `/tasks/{id}/push` | Push completed task to remote git |
| POST | `/tasks/{id}/cleanup` | Initiate cleanup (transitions to cleaning_up) |

### POST /tasks — CreateTaskRequest

```json
{
  "task_type": "build_feature",
  "project_id": "uuid (optional, omit for new project)",
  "project_name": "string (required for scaffold_project)",
  "git_url": "string (required for non-scaffold types)",
  "branch": "string (optional, required for review_code)",
  "commits_to_review": 5,
  "agent_id": "uuid (required)",
  "requirement": "string (required)",
  "required_capabilities": ["python", "docker"]
}
```

### GET /tasks — TaskResponse

```json
{
  "id": "uuid",
  "project_name": "string",
  "agent_display_name": "string",
  "status": "pending",
  "task_type": "build_feature",
  "requirement": "string",
  "created_at": "datetime"
}
```

### GET /tasks/{id} — TaskDetailResponse

Extends TaskResponse with: `git_url`, `branch`, `task_type`, `commits_to_review`, `work_directory_path`, `started_at`, `completed_at`, `error_message`, `assigned_worker_id`, `assigned_worker_url`, `required_capabilities`, `assigned_sandbox_id`, `assigned_sandbox_url`.

### PATCH /tasks/{id}

- `{"status": "aborted"}` — abort a pending task
- `{"status": "pending", ...fields}` — resubmit an aborted task

## Service Architecture

Tasks are created via the API service and stored in PostgreSQL. The controller service polls the database for pending tasks and delegates them to available workers. The API exposes proxy endpoints for push and cleanup operations.

```
User → Web UI → API (POST /tasks) → PostgreSQL
                                         ↓
                              Controller (poll loop)
                                         ↓
                              Worker (execute agent)
                                         ↓
                              Controller (heartbeat/status)
                                         ↓
                              API (PATCH status)
```

## UI Components

### TaskForm (`web/src/app/tasks/new/`)

- Task Type dropdown (6 options) — conditionally shows/hides fields
- Project selector: "New Project" or existing project
- Project Name field (for scaffold tasks)
- Git URL field (required for non-scaffold)
- Branch field (optional, required for review_code)
- Commits to Review (optional, review_code only)
- Agent selector (populated from `GET /agents`)
- Required Capabilities: comma-separated input field (optional, shown for all task types)
- Requirements textarea

### TaskTable (`web/src/app/tasks/`)

- Columns: Project name, Agent, Task Type badge, Status badge, Created date, Actions
- Client-side search filters by requirement text and project name
- Actions: Abort (pending only), Edit (aborted only)

### StatusBadge (`web/src/components/tasks/StatusBadge.tsx`)

Color-coded badges for all 7 statuses: pending (blue), in_progress (purple), completed (green), failed (red), aborted (yellow), cleaning_up (orange), cleaned (gray).

### Task Detail Page (`web/src/app/tasks/[id]/page.tsx`)

- Task metadata: status, type, project, agent, requirement, git URL, branch
- In Progress: elapsed time counter
- Completed/Failed: Push to Remote button, Clean Up button, Source Code section
- Failed: error message display
- Shows capability badges when `required_capabilities` are set
- Shows sandbox ID when a sandbox is allocated
- Files tab available for pending/in_progress tasks (not just completed/failed) — see Source Code Browser context

## Configuration

No task-specific configuration. Task behavior is determined by agent settings and controller polling intervals (see orchestration and agent-execution contexts).

## Cross-Context Dependencies

- **Orchestration**: Controller delegates pending tasks to workers, manages lease renewal, handles cleanup flow
- **Agent Execution**: Workers execute the actual coding agent and report status back
- **Source Code Browser**: Completed/failed tasks expose generated files via worker's file endpoints
- **Git Integration**: Push to remote uses worker's push endpoint; clone uses GitHub token from settings
- **Platform Infrastructure**: Projects and agents are referenced by tasks; settings store LLM config
