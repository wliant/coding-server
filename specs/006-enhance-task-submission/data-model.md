# Data Model: Enhanced Task Submission

**Feature**: 006-enhance-task-submission
**Date**: 2026-03-06

## New Entity: Agent

Represents an available agent library that the system can invoke. Stored in a dedicated `agents` database table so agents can be added or removed without a code deploy.

| Field         | Type             | Constraints                       | Notes                                          |
|---------------|------------------|-----------------------------------|------------------------------------------------|
| `id`          | UUID             | PK, generated                     | System-assigned identifier                     |
| `identifier`  | String(100)      | NOT NULL, UNIQUE                  | Machine-readable key; maps to agent library    |
| `display_name`| String(255)      | NOT NULL                          | Human-readable name shown in the UI            |
| `is_active`   | Boolean          | NOT NULL, default `true`          | Inactive agents are hidden from the UI         |
| `created_at`  | DateTime (TZ)    | NOT NULL, server default `now()`  | Immutable; set at row creation                 |

**Initial seed data** (inserted in migration 0005):

| identifier                  | display_name                  |
|-----------------------------|-------------------------------|
| `spec_driven_development`   | Spec-Driven Development       |
| `generic_testing`           | Generic Testing               |

**State transitions**: `is_active` can be toggled by an admin via direct SQL. There is no lifecycle state machine; the field is a simple boolean filter.

**Validation rules**:
- `identifier` must be unique across all rows.
- `display_name` must be non-empty.

---

## Modified Entity: Job (jobs table)

New column added. Two existing columns deprecated (retained in DB, ignored by new business logic).

| Field              | Change    | Type        | Constraints                          | Notes                                                     |
|--------------------|-----------|-------------|--------------------------------------|-----------------------------------------------------------|
| `agent_id`         | **NEW**   | UUID        | NULLABLE, FK → agents.id             | Null for legacy tasks. Present for all new tasks.        |
| `dev_agent_type`   | deprecated| String(50)  | NOT NULL (kept as-is)                | Legacy field; ignored by new code. Not removed from DB.  |
| `test_agent_type`  | deprecated| String(50)  | NOT NULL (kept as-is)                | Legacy field; ignored by new code. Not removed from DB.  |

All other `jobs` columns are unchanged.

**Migration plan**:
- Migration 0005: Create `agents` table (no change to `jobs`).
- Migration 0006: Add `agent_id` (nullable UUID, FK → agents.id, named constraint `fk_jobs_agent_id`) to `jobs`. No backfill. No server default.

---

## Unchanged Entity: Project (projects table)

No DB schema changes. Existing nullable `name` and `git_url` columns accommodate the new validation requirements at the API layer.

| Field       | Type          | Existing Constraints | API-layer rule (new)                                           |
|-------------|---------------|----------------------|----------------------------------------------------------------|
| `name`      | String(255)   | NULLABLE             | Required (non-empty) in `CreateTaskRequest` when `project_type = "new"` |
| `git_url`   | Text          | NULLABLE             | Required in `CreateTaskRequest` when `project_type = "existing"` |
| `source_type` | String(20) | NOT NULL             | Unchanged (`new` / `existing`)                                 |

---

## API Schema Changes

### CreateTaskRequest (modified)

| Field             | Change                  | Type             | Required         | Notes                                             |
|-------------------|-------------------------|------------------|------------------|---------------------------------------------------|
| `project_type`    | unchanged               | `"new"/"existing"` | yes             |                                                   |
| `project_id`      | unchanged               | UUID \| null     | no               | Required at runtime when `project_type = "existing"` |
| `project_name`    | **NEW**                 | string \| null   | no               | Required at runtime when `project_type = "new"`, validated by `@model_validator` |
| `agent_id`        | **NEW**                 | UUID             | **yes**          | Must reference an active agent in the registry    |
| `git_url`         | unchanged               | string \| null   | no               | Required at runtime when `project_type = "existing"` |
| `requirements`    | unchanged               | string           | yes              | min_length=1                                      |
| `dev_agent_type`  | **deprecated, optional**| enum \| null     | no               | Default applied; ignored when `agent_id` present  |
| `test_agent_type` | **deprecated, optional**| enum \| null     | no               | Default applied; ignored when `agent_id` present  |

**Cross-field validation** (implemented as `@model_validator(mode="after")`):
1. If `project_type == "new"` → `project_name` must be non-empty string.
2. If `project_type == "existing"` → `project_id` must be present; `git_url` must be non-empty.
3. `agent_id` must be present (already enforced by required typing).

### PushTaskRequest (new)

| Field     | Type           | Required | Notes                                                                |
|-----------|----------------|----------|----------------------------------------------------------------------|
| `git_url` | string \| null | no       | If provided, saves to `project.git_url` before executing the push   |

Entire body is optional. Callers can omit it, send `{}`, or send `{"git_url": "..."}`.

### AgentSummary (new — embedded in task responses)

| Field          | Type   | Notes                              |
|----------------|--------|------------------------------------|
| `id`           | UUID   | Agent's primary key                |
| `identifier`   | string | Machine-readable agent identifier  |
| `display_name` | string | Human-readable name for the UI     |

### AgentResponse (new — returned by GET /agents)

All fields from `AgentSummary` plus:

| Field        | Type     | Notes                   |
|--------------|----------|-------------------------|
| `is_active`  | boolean  | Always `true` in list   |
| `created_at` | datetime | ISO 8601 with TZ        |

### TaskResponse (modified)

| Field             | Change                  | Notes                                             |
|-------------------|-------------------------|---------------------------------------------------|
| `agent`           | **NEW** — nullable      | `AgentSummary \| null`; null for legacy tasks     |
| `dev_agent_type`  | deprecated              | Retained for backward compat; nullable in schema  |
| `test_agent_type` | deprecated              | Retained for backward compat; nullable in schema  |

### TaskDetailResponse (modified)

Same changes as `TaskResponse`. `project` field already includes `git_url` via `ProjectSummaryWithGitUrl`.
