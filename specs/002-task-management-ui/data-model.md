# Data Model: Basic UI & Task Management

**Branch**: `002-task-management-ui` | **Date**: 2026-03-03

## Entity Overview

```
┌──────────────┐      1       ┌──────────────┐
│   Project    │──────────────│     Job      │
│  (projects)  │              │    (jobs)    │
└──────────────┘              └──────────────┘

┌──────────────┐
│   Setting    │  (standalone, no relations)
│  (settings)  │
└──────────────┘
```

---

## Entity: Project (existing table, no schema changes)

**Table**: `projects`

| Column        | Type                      | Constraints                | Notes                                      |
|---------------|---------------------------|----------------------------|--------------------------------------------|
| `id`          | UUID                      | PK, server_default gen_random_uuid() | |
| `name`        | VARCHAR(255)              | NULLABLE                   | Null for "New Project" until agent assigns |
| `source_type` | VARCHAR(20)               | NOT NULL                   | `"new"` for UI-created; `"git"` future     |
| `git_url`     | TEXT                      | NULLABLE                   | Future; null for `source_type = "new"`     |
| `status`      | VARCHAR(20)               | NOT NULL, default `"active"` |                                          |
| `created_at`  | TIMESTAMPTZ               | NOT NULL, server_default now() |                                        |
| `updated_at`  | TIMESTAMPTZ               | NOT NULL, server_default now() |                                        |

**Validation rules**:
- `source_type` ∈ `{ "new", "git" }` (enforced in service layer)
- `status` ∈ `{ "active", "archived" }` (enforced in service layer)
- `name` may be null only when `source_type = "new"`

**Query patterns**:
- `GET /projects` → `SELECT * FROM projects WHERE name IS NOT NULL AND status = 'active'`

---

## Entity: Job / Task (existing table, **modified**)

**Table**: `jobs`

| Column            | Type        | Constraints                               | Notes                                          |
|-------------------|-------------|-------------------------------------------|------------------------------------------------|
| `id`              | UUID        | PK, server_default gen_random_uuid()      |                                                |
| `project_id`      | UUID        | NOT NULL, FK → projects.id                |                                                |
| `requirement`     | TEXT        | NOT NULL                                  | Maps to "Requirements" in the UI               |
| `dev_agent_type`  | VARCHAR(50) | NOT NULL, default `'spec_driven_development'` | **NEW COLUMN** (migration 0002)           |
| `test_agent_type` | VARCHAR(50) | NOT NULL, default `'generic_testing'`     | **NEW COLUMN** (migration 0002)                |
| `status`          | VARCHAR(20) | NOT NULL, default `'pending'`             | Default changed from `'queued'` (migration 0002) |
| `created_at`      | TIMESTAMPTZ | NOT NULL, server_default now()            |                                                |
| `started_at`      | TIMESTAMPTZ | NULLABLE                                  | Set by worker on pickup                        |
| `completed_at`    | TIMESTAMPTZ | NULLABLE                                  | Set by worker on finish                        |
| `error_message`   | TEXT        | NULLABLE                                  | Populated on `failed` status                   |

**Status lifecycle**:

```
pending ──────────────────────────────► in_progress ──► completed
   │                                                  └──► failed
   └──► aborted ──► pending  (edit + resubmit only)
```

**Allowed status transitions** (enforced in `task_service`):

| From         | To           | Triggered by          |
|--------------|--------------|-----------------------|
| `pending`    | `aborted`    | User abort action     |
| `pending`    | `in_progress`| Worker pickup         |
| `aborted`    | `pending`    | User edit + resubmit  |
| `in_progress`| `completed`  | Worker completion     |
| `in_progress`| `failed`     | Worker error          |

**Validation rules**:
- `dev_agent_type` ∈ `{ "spec_driven_development" }` (extensible; enforced in service layer)
- `test_agent_type` ∈ `{ "generic_testing" }` (extensible; enforced in service layer)
- `requirement` MUST NOT be empty
- `project_id` MUST reference an existing project

**Query patterns**:
- `GET /tasks` → `SELECT j.*, p.name, p.source_type FROM jobs j JOIN projects p ON j.project_id = p.id ORDER BY j.created_at DESC`
- `POST /tasks` → INSERT project (if new) then INSERT job
- `PATCH /tasks/{id}` → UPDATE jobs SET ... WHERE id = ? (with transition validation)

---

## Entity: Setting (new table)

**Table**: `settings`

| Column       | Type         | Constraints                    | Notes                          |
|--------------|--------------|--------------------------------|--------------------------------|
| `key`        | VARCHAR(100) | PK                             | Dot-notation, e.g. `agent.work.path` |
| `value`      | TEXT         | NOT NULL                       | Stored as string; interpreted by consumer |
| `updated_at` | TIMESTAMPTZ  | NOT NULL, server_default now(), onupdate now() | |

**Initial data** (seeded on first `GET /settings` if missing):

| key               | default value |
|-------------------|---------------|
| `agent.work.path` | `""`          |

**Validation rules**:
- `key` follows dot-notation convention; validated against allowed key list in service layer
- `value` may be empty string (user clears the field)

**Query patterns**:
- `GET /settings` → `SELECT key, value FROM settings`
- `PUT /settings` → `INSERT INTO settings (key, value, updated_at) VALUES ... ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = now()`

---

## Migration Plan

### Migration 0002: `0002_add_task_fields_and_settings`

**upgrade()**:
1. Add `dev_agent_type` VARCHAR(50) NOT NULL DEFAULT `'spec_driven_development'` to `jobs`
2. Add `test_agent_type` VARCHAR(50) NOT NULL DEFAULT `'generic_testing'` to `jobs`
3. Change column default for `jobs.status` from `'queued'` to `'pending'`
4. Create `settings` table with columns `key`, `value`, `updated_at`

**downgrade()**:
1. Drop `settings` table
2. Revert `jobs.status` default to `'queued'`
3. Drop `test_agent_type` from `jobs`
4. Drop `dev_agent_type` from `jobs`
