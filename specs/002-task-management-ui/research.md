# Research: Basic UI & Task Management

**Branch**: `002-task-management-ui` | **Date**: 2026-03-03

## Decision 1: "Task" naming vs. existing `Job` model

**Decision**: Keep the database model and table named `Job` / `jobs`; expose the resource as `/tasks` in the API URLs. The spec and UI use "Task" terminology; the worker and internal code use "Job".

**Rationale**: The `Job` model already exists in the DB with a valid migration. Renaming it would require updating the worker service (which uses BLMOVE on Redis keyed to jobs). Exposing `/tasks` as the API path is a clean translation layer — the API contract is spec-aligned while the DB schema remains stable.

**Alternatives considered**:
- Rename `Job` → `Task` everywhere: Would align naming end-to-end but requires worker changes outside this feature's scope. Rejected — out of scope.
- Add a `tasks` view alias in Postgres: Adds unnecessary indirection. Rejected — YAGNI.

---

## Decision 2: Job status vocabulary

**Decision**: Align the `jobs.status` column values with the spec: `pending`, `aborted`, `in_progress`, `completed`, `failed`. The existing default `"queued"` is replaced with `"pending"` via a migration.

**Rationale**: Consistency between API response values, UI display, and DB storage eliminates mapping logic. Since no production data exists yet, the change is safe.

**Alternatives considered**:
- Keep `"queued"` and map to `"pending"` in the service layer: Adds unnecessary translation. Rejected — YAGNI.

---

## Decision 3: New columns on `jobs` table

**Decision**: Add `dev_agent_type` (VARCHAR 50, NOT NULL, default `'spec_driven_development'`) and `test_agent_type` (VARCHAR 50, NOT NULL, default `'generic_testing'`) to the existing `jobs` table via a new Alembic migration (`0002`).

**Rationale**: The spec requires these fields on every task. They belong on `jobs` since a job is always executed by a specific agent pair. Using string column with a default allows future agent types to be added without schema changes.

**Alternatives considered**:
- Separate `job_agents` table: Over-engineered for two fields with static values. Rejected.
- Enum column type: Prevents adding new agent types without a migration. Rejected — simpler string is sufficient.

---

## Decision 4: Settings storage

**Decision**: A `settings` table with `key` (VARCHAR 100, PK), `value` (TEXT NOT NULL), `updated_at` (TIMESTAMPTZ). One row per setting, upserted on save.

**Rationale**: Single-table key-value is the simplest structure that satisfies FR-004 (persist across reloads), FR-005 (read current values), and FR-006 (explicit save). The General tab currently has one property (`agent.work.path`); additional properties are trivially added as new rows.

**Alternatives considered**:
- JSONB column in a single `app_config` row: Harder to query individual keys; no advantage for <10 settings. Rejected.
- Flat config file (JSON/YAML on disk): Cannot be read/written by the API without filesystem access concerns in Docker. Rejected.

---

## Decision 5: Search implementation (client-side vs. backend)

**Decision**: Client-side filtering in the browser. The frontend fetches all tasks once and filters in memory on every keystroke.

**Rationale**: SC-002 requires results within 1 second for ≤500 tasks. Filtering 500 rows in JavaScript is near-instant (<5ms). A backend search API would add network round-trips on each keystroke, increasing latency. The spec sets a hard ceiling of 500 tasks for this feature.

**Alternatives considered**:
- Backend full-text search (`ILIKE` or `tsvector`): Higher latency per keystroke; adds query complexity. Unnecessary at ≤500 rows. Rejected.
- Debounced backend search: Still slower than in-memory; complexity not justified. Rejected.

---

## Decision 6: UI component library

**Decision**: **Tailwind CSS** (utility classes) + **shadcn/ui** (headless accessible components). The web package currently has no styling framework.

**Rationale**: This feature requires a non-trivial UI surface: data table, multi-select dropdown, dialog, tabs, textarea, form validation states. shadcn/ui provides accessible, composable primitives that integrate naturally with Next.js 15 App Router and React 19. Tailwind is already the de-facto companion. Building these from scratch with plain CSS would take significantly longer with no architectural benefit.

**Alternatives considered**:
- Plain CSS modules: Sufficient for trivial UIs but would require hand-rolling dialog, select, and table from scratch. Rejected — time cost unjustified.
- MUI / Ant Design: Heavier bundle, harder to customise, not optimised for App Router RSC. Rejected.

---

## Decision 7: "New Project" creation flow

**Decision**: When `project_type = "new"` is submitted, the API creates a `Project` record with `source_type = "new"` and `name = null`. The existing project record's ID is stored as `jobs.project_id`. The agent later assigns a name.

`GET /projects` returns only projects where `name IS NOT NULL` (named, existing projects). This gives the frontend a clean list of selectable "Existing Project" options.

**Rationale**: Aligns with A-006 (naming handled by agent later). The "New Project" option in the frontend dropdown is a static UI choice, not a project record lookup. The backend creates a nameless project stub on submission.

**Alternatives considered**:
- Require a name at "New Project" submission: Changes the spec (A-006 explicitly defers naming). Rejected.
- Store `project_type` flag on the job (not create a project at all): Breaks the FK relationship and prevents future project-based lookups. Rejected.

---

## Decision 8: API shape for task abort vs. edit

**Decision**: Single `PATCH /tasks/{id}` endpoint handles both abort and edit+resubmit. The request body contains only the fields being changed:
- Abort: `{ "status": "aborted" }` (only valid from `pending`)
- Edit+Resubmit: `{ "requirements": "...", "dev_agent_type": "...", "test_agent_type": "...", "project_id": "...", "status": "pending" }` (only valid from `aborted`)

The service layer validates the transition and returns `422` if the transition is invalid.

**Rationale**: A single PATCH endpoint is idiomatic REST for partial resource updates. Two separate endpoints (`/abort`, `/resubmit`) would be RPC-style and add unnecessary routing complexity.

**Alternatives considered**:
- `POST /tasks/{id}/abort` and `POST /tasks/{id}/resubmit`: Clearer intent but deviates from REST conventions. Rejected.
- `PUT /tasks/{id}` (full replacement): Requires sending all fields for an abort (wasteful). Rejected.
