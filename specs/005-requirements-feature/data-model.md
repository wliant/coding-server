# Data Model: Automated Task Execution via Agent Worker

**Feature**: 005-requirements-feature | **Date**: 2026-03-06

## Changes to Existing Models

### `jobs` table — new columns (migration `0004`)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `lease_holder` | `VARCHAR(36)` | YES | NULL | UUID of the worker instance holding the execution lease |
| `lease_expires_at` | `TIMESTAMPTZ` | YES | NULL | UTC timestamp when the current lease expires; NULL when not leased |

**Validation rules**:
- Both columns are set atomically during lease acquisition via a conditional `UPDATE … WHERE status = 'pending'`.
- Both are reset to `NULL` when a task completes (Completed or Failed) or when the lease reaper returns the task to Pending.
- `lease_holder` is a worker-generated UUID (not a FK; workers are ephemeral).

**State transition invariants**:

```
Pending   → In Progress : lease_holder = <worker_uuid>, lease_expires_at = now() + TTL
In Progress → Completed  : lease_holder = NULL, lease_expires_at = NULL, completed_at = now()
In Progress → Failed     : lease_holder = NULL, lease_expires_at = NULL, completed_at = now(), error_message = <msg>
In Progress → Pending    : (lease reaper) lease_holder = NULL, lease_expires_at = NULL  [when lease_expires_at < now()]
Pending   → Aborted      : (spec 002 UI) no change to lease columns
```

### `projects` table — no new columns

`Project.git_url` (nullable `TEXT`) already exists from migration `0001`. This feature uses it as the push target. The spec 002 task submission form must ensure `git_url` is supplied for new projects; this is a spec 002 concern, not a schema change here.

---

## Unchanged Models

### `work_directories` table

No changes. The worker creates a `WorkDirectory` record before invoking the agent:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Auto-generated |
| `job_id` | UUID FK → jobs.id | One-to-one with Job (UNIQUE constraint) |
| `path` | TEXT UNIQUE | Absolute path: `{AGENT_WORK_PARENT}/{job_id}` |
| `created_at` | TIMESTAMPTZ | Worker creation time |

### `settings` table

No changes.

---

## New Pydantic Schemas

### `TaskDetailResponse` (extends `TaskResponse`)

```
id: UUID
project: ProjectSummary          # id, name, source_type, git_url
dev_agent_type: DevAgentType
test_agent_type: TestAgentType
requirements: str
status: TaskStatus               # pending | in_progress | completed | failed | aborted
created_at: datetime
updated_at: datetime
started_at: datetime | None
completed_at: datetime | None
error_message: str | None
work_directory_path: str | None  # from WorkDirectory.path; None if not yet claimed
elapsed_seconds: int | None      # computed: (now - started_at).seconds if in_progress; else None
```

### `CreateTaskRequest` — extended

Adds `git_url: str | None = None` field. When `project_type = "new"`, `git_url` is stored in `Project.git_url`. When `project_type = "existing"`, `git_url` is ignored (project already has its URL).

### `PushResponse`

```
branch_name: str     # e.g. "task/a1b2c3d4"
remote_url: str      # Project.git_url
pushed_at: datetime  # UTC timestamp of successful push
```

---

## Migration: `0004_add_job_lease_fields.py`

```python
# Adds lease_holder (VARCHAR 36, nullable) and lease_expires_at (TIMESTAMPTZ, nullable) to jobs.
# Down: drops both columns.
```

No index needed on `lease_expires_at` at this scale; the lease reaper query covers only the single active worker's task.
