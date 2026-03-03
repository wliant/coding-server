# Tasks: Basic UI & Task Management

**Input**: Design documents from `/specs/002-task-management-ui/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/api.yaml ✅, quickstart.md ✅

**Tests**: Included — Constitution Principle II (TDD) is NON-NEGOTIABLE. Tests MUST be written first and MUST fail before implementation begins.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no mutual dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install new dependencies and write the database migration before any feature work begins.

- [x] T001 Install Tailwind CSS and shadcn/ui: add `tailwindcss`, `@tailwindcss/postcss`, `shadcn/ui` and required peer deps to `web/package.json`; create `web/tailwind.config.ts` and `web/postcss.config.mjs`; add Tailwind directives to `web/src/app/globals.css`; run `npx shadcn init` to generate `web/src/components/ui/` primitives (button, dialog, input, select, tabs, textarea)
- [x] T002 Write Alembic migration `0002_add_task_fields_and_settings` in `api/alembic/versions/0002_add_task_fields_and_settings.py`: upgrade adds `dev_agent_type` VARCHAR(50) NOT NULL DEFAULT `'spec_driven_development'` and `test_agent_type` VARCHAR(50) NOT NULL DEFAULT `'generic_testing'` to `jobs`; changes `jobs.status` column default from `'queued'` to `'pending'`; creates `settings` table with `key` VARCHAR(100) PK, `value` TEXT NOT NULL, `updated_at` TIMESTAMPTZ NOT NULL server_default now(). Downgrade reverses all changes.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pydantic schemas, SQLAlchemy model, stub routes with correct response shapes, OpenAPI export, and navigation shell. MUST be complete before any user story work begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 [P] Create `Setting` SQLAlchemy model in `api/src/api/models/setting.py`: `key` (String 100, PK), `value` (Text, NOT NULL), `updated_at` (DateTime timezone=True, server_default + onupdate now()), mapped to table `settings`, using same `Base` from `api/src/api/models/project.py`
- [x] T004 [P] Update `api/src/api/db.py` to import `Setting` from `api.models.setting` so Alembic metadata includes the new table
- [x] T005 [P] Create `api/src/api/schemas/task.py`: `TaskStatus` str enum (pending, aborted, in_progress, completed, failed); `DevAgentType` str enum (spec_driven_development); `TestAgentType` str enum (generic_testing); `ProjectType` str enum (new, existing); `TaskResponse` (id UUID, project ProjectSummary, dev_agent_type, test_agent_type, requirements str, status TaskStatus, created_at datetime, updated_at datetime, error_message str|None); `CreateTaskRequest` (project_type ProjectType, project_id UUID|None, dev_agent_type DevAgentType, test_agent_type TestAgentType, requirements str minlength=1); `UpdateTaskRequest` all fields Optional
- [x] T006 [P] Create `api/src/api/schemas/project.py`: `ProjectSummary` (id UUID, name str|None, source_type str)
- [x] T007 [P] Create `api/src/api/schemas/setting.py`: `SettingsResponse` (settings: dict[str, str]); `UpdateSettingsRequest` (settings: dict[str, str])
- [x] T008 [P] Create stub `api/src/api/routes/tasks.py`: `GET /tasks` returns `list[TaskResponse]` (empty list); `POST /tasks` accepts `CreateTaskRequest`, returns `TaskResponse` stub with status 201; `PATCH /tasks/{task_id}` accepts `UpdateTaskRequest`, returns `TaskResponse` stub — all stubs return `JSONResponse(status_code=501)` body. Correct schema annotations required for OpenAPI export.
- [x] T009 [P] Update `api/src/api/routes/projects.py`: change `GET /projects` return type annotation to `list[ProjectSummary]` (keep stub returning `[]`); remove all other stub routes that are not part of this feature's contract
- [x] T010 [P] Create stub `api/src/api/routes/settings.py`: `GET /settings` returns `SettingsResponse` (stub); `PUT /settings` accepts `UpdateSettingsRequest`, returns `SettingsResponse` (stub 501)
- [x] T011 Register `tasks` and `settings` routers in `api/src/api/main.py`: import and `app.include_router(tasks.router)`, `app.include_router(settings.router)`; verify all 6 new routes appear at `GET /openapi.json`
- [x] T012 Export updated OpenAPI spec and regenerate TypeScript client: run `make generate` from repo root; verify `openapi.json` at repo root contains paths for `/tasks`, `/projects`, `/settings`; verify `web/src/client/` is generated with corresponding typed functions
- [x] T013 Create navigation sidebar and update root layout: create `web/src/components/nav/Sidebar.tsx` with links to `/tasks` (Task List), `/tasks/new` (Submit Task), and `/settings` (Settings) using Next.js `Link`; update `web/src/app/layout.tsx` to include `Sidebar` in a flex layout wrapper; update `web/src/app/page.tsx` to redirect to `/tasks` using Next.js `redirect()`

**Checkpoint**: All 6 new API routes visible in OpenAPI spec, TS client generated, navigation shell renders in browser.

---

## Phase 3: User Story 1 — Submit a New Task (Priority: P1) 🎯 MVP

**Goal**: Users can fill out the task submission form, select a project (new or existing), choose agent types, enter requirements, and submit. The task is created with "pending" status.

**Independent Test**: Submit a task via `POST /tasks` with `project_type: "new"`, verify 201 response with `status: "pending"` and a valid UUID. Navigate to `/tasks/new`, fill and submit the form, verify redirect to `/tasks` and the new task appears.

> **⚠️ Write tests FIRST. Run them. Confirm they FAIL before writing any implementation.**

- [x] T014 [P] [US1] Write failing unit tests for `project_service` in `api/tests/unit/test_project_service.py`: test `list_named_projects()` returns only projects where name IS NOT NULL; test `create_project(source_type="new")` inserts a row with name=None; use `db_session` fixture from `conftest.py`
- [x] T015 [P] [US1] Write failing unit tests for task create in `api/tests/unit/test_task_service.py`: test `create_task()` with new project creates both a Project and a Job row; test `create_task()` with existing project_id creates only a Job row; test `create_task()` with invalid project_id raises 422; use `db_session` fixture
- [x] T016 [US1] Write failing integration tests for `POST /tasks` and `GET /projects` in `api/tests/integration/test_tasks_api.py`: test POST with `project_type="new"` returns 201 with `status="pending"`; test POST with missing requirements returns 422; test POST with `project_type="existing"` and invalid project_id returns 422; test GET `/projects` returns only named projects
- [x] T017 [P] [US1] Create `api/src/api/services/project_service.py`: `async def list_named_projects(db)` → SELECT projects WHERE name IS NOT NULL AND status='active'; `async def create_project(db, source_type="new")` → INSERT project with name=None, return Project ORM object
- [x] T018 [US1] Create `api/src/api/services/task_service.py`: `async def create_task(db, req: CreateTaskRequest)` → calls `create_project()` when `project_type="new"` or validates existing `project_id`; INSERTs Job with dev_agent_type, test_agent_type, requirement, status="pending"; returns Job ORM object joined with Project
- [x] T019 [US1] Implement `GET /projects` and `POST /tasks` in their respective route files: replace 501 stubs with real DB calls via `project_service` and `task_service`; inject `db: AsyncSession = Depends(get_db)`; return properly serialised `ProjectSummary` / `TaskResponse` objects; all unit + integration tests must pass
- [x] T020 [P] [US1] Write failing `web/tests/unit/TaskForm.test.tsx`: test form renders all 4 fields (project dropdown, dev agent select, test agent select, requirements textarea); test submit button is disabled when requirements is empty; test submit button is disabled when no project selected; test form calls `onSubmit` callback with correct values when valid
- [x] T021 [US1] Create `web/src/components/tasks/TaskForm.tsx`: client component; props: `projects: ProjectSummary[]`, `onSubmit: (data) => Promise<void>`, `initialValues?: TaskFormValues`, `isSubmitting?: boolean`; renders shadcn/ui `Select` for project (options: "New Project" + each project by name), `Select` for dev agent type (only "Spec Driven Development Agent"), `Select` for test agent type (only "Generic Testing Agent"), `Textarea` for requirements; client-side validation: all fields required; submit button disabled while submitting; all `TaskForm` unit tests must pass
- [x] T022 [US1] Create `web/src/app/tasks/new/page.tsx`: server component that fetches projects via generated client `listProjects()`; renders page heading and `<TaskForm>`; on form submit calls `createTask()` from generated client; on success uses `router.push('/tasks')`; on error displays error message

**Checkpoint**: `POST /tasks` returns 201 with correct schema. `/tasks/new` form submits and redirects to `/tasks`. US1 independently testable end-to-end.

---

## Phase 4: User Story 2 — View and Search Task List (Priority: P2)

**Goal**: Users see all submitted tasks in a table with status, project, and dates. A search box filters tasks in real time by requirement text or project name.

**Independent Test**: Submit 3 tasks with distinct requirements. Navigate to `/tasks`. Verify all 3 appear. Type a keyword in the search box; verify only matching rows are shown. Clear search; verify all 3 return.

> **⚠️ Write tests FIRST. Run them. Confirm they FAIL before writing any implementation.**

- [x] T023 [US2] Write failing integration tests for `GET /tasks` in `api/tests/integration/test_tasks_api.py` (add to existing file): test GET returns all tasks ordered by created_at DESC; test response includes `project` object with name and source_type; test empty list returned when no tasks exist
- [x] T024 [US2] Implement `GET /tasks` in `api/src/api/routes/tasks.py`: replace 501 stub; SELECT jobs JOIN projects ORDER BY jobs.created_at DESC; serialise each row as `TaskResponse`; integration tests must pass
- [x] T025 [P] [US2] Write failing `web/tests/unit/TaskTable.test.tsx`: test table renders column headers (Project, Dev Agent, Test Agent, Status, Submitted); test all provided tasks render as rows; test search input filters rows to only those whose requirements or project name contain the search term; test empty state message shown when task list is empty; test empty state message shown when search matches nothing
- [x] T026 [US2] Create `web/src/components/tasks/TaskTable.tsx`: client component; props: `tasks: TaskResponse[]`; renders shadcn/ui `Input` for search (client-side filter on `requirements` + `project.name`); renders HTML table with columns: Project (shows project name or "New Project" if null), Dev Agent, Test Agent, Status (as plain text badge), Submitted date; shows empty state message when `tasks` is empty or search matches nothing; no action buttons yet (added in US3/US4); all `TaskTable` unit tests must pass
- [x] T027 [US2] Create `web/src/app/tasks/page.tsx`: server component that fetches tasks via generated client `listTasks()`; renders page heading, "Submit Task" link button, and `<TaskTable tasks={tasks} />`

**Checkpoint**: `/tasks` page lists all tasks. Search filters rows client-side. US2 independently testable.

---

## Phase 5: User Story 3 — Abort a Pending Task (Priority: P3)

**Goal**: An Abort button appears on each "pending" task row. Clicking shows a confirmation dialog. On confirm, the task status changes to "aborted" and the Abort button disappears.

**Independent Test**: Create a pending task. Verify the Abort button appears. Click Abort, confirm. Verify the task row now shows "aborted" status and has no Abort button.

> **⚠️ Write tests FIRST. Run them. Confirm they FAIL before writing any implementation.**

- [x] T028 [P] [US3] Write failing unit tests for abort transition in `api/tests/unit/test_task_service.py` (add test cases): test `update_task_status(id, "aborted")` on a pending task succeeds; test it on an in_progress task raises 422 with "invalid transition" message; test it on an already-aborted task raises 422
- [x] T029 [US3] Write failing integration tests for abort in `api/tests/integration/test_tasks_api.py` (add cases): test `PATCH /tasks/{id}` with `{"status": "aborted"}` on a pending task returns 200 with `status="aborted"`; test on a non-pending task returns 422; test on a non-existent ID returns 404
- [x] T030 [US3] Add `async def abort_task(db, task_id)` to `api/src/api/services/task_service.py`: validates current status is "pending" (raises HTTPException 422 otherwise); updates `jobs.status` to "aborted"; returns updated Job; unit tests must pass
- [x] T031 [US3] Implement `PATCH /tasks/{task_id}` for abort in `api/src/api/routes/tasks.py`: when request body contains `status="aborted"`, delegates to `task_service.abort_task()`; returns 404 if task not found; returns 422 on invalid transition; integration tests must pass
- [x] T032 [P] [US3] Create `web/src/components/tasks/AbortConfirmDialog.tsx`: client component using shadcn/ui `Dialog`; props: `open: boolean`, `onConfirm: () => void`, `onCancel: () => void`, `isLoading?: boolean`; renders confirmation message "Are you sure you want to abort this task?"; Confirm button (destructive variant), Cancel button; Confirm disabled while `isLoading`
- [x] T033 [US3] Add Abort action to `web/src/components/tasks/TaskTable.tsx`: add an Actions column; render `AbortConfirmDialog` (initially closed); for each task with `status === "pending"`, render an Abort button that opens the dialog; on confirm, call `updateTask({ taskId, body: { status: "aborted" } })` from generated client; on success, update local task list state to reflect new status (optimistic update or re-fetch)

**Checkpoint**: Pending tasks have Abort button. Confirm aborts the task. Non-pending tasks have no Abort button. US3 independently testable.

---

## Phase 6: User Story 4 — Edit an Aborted Task and Resubmit (Priority: P4)

**Goal**: An Edit button appears on each "aborted" task row. Clicking opens a pre-populated form. Saving updates the task fields and status returns to "pending".

**Independent Test**: Abort a task. Click Edit. Verify form is pre-populated with original values. Update requirements text. Submit. Verify task returns to "pending" status with the new requirements.

> **⚠️ Write tests FIRST. Run them. Confirm they FAIL before writing any implementation.**

- [x] T034 [P] [US4] Write failing unit tests for edit+resubmit in `api/tests/unit/test_task_service.py` (add cases): test `resubmit_task(id, updates)` on an aborted task succeeds and status returns to "pending"; test it on a pending task raises 422; test it on a completed task raises 422; test that updated fields (requirements, dev_agent_type) are persisted
- [x] T035 [US4] Write failing integration tests for resubmit in `api/tests/integration/test_tasks_api.py` (add cases): test `PATCH /tasks/{id}` with `{"status": "pending", "requirements": "updated text"}` on an aborted task returns 200 with updated fields and `status="pending"`; test on a non-aborted task returns 422; test on non-existent ID returns 404
- [x] T036 [US4] Add `async def resubmit_task(db, task_id, updates: UpdateTaskRequest)` to `api/src/api/services/task_service.py`: validates current status is "aborted" (raises 422 otherwise); applies provided field updates; sets status to "pending"; returns updated Job; unit tests must pass
- [x] T037 [US4] Implement `PATCH /tasks/{task_id}` for resubmit in `api/src/api/routes/tasks.py`: when request body contains `status="pending"`, delegates to `task_service.resubmit_task()`; merge with existing abort handling (route dispatches to abort_task or resubmit_task based on target status); integration tests must pass
- [x] T038 [US4] Create `web/src/app/tasks/[id]/edit/page.tsx`: server component; fetches task by ID via `listTasks()` (filter by id) or a GET `/tasks/{id}` if available; if task status is not "aborted", redirects to `/tasks`; renders `<TaskForm initialValues={task} projects={projects} onSubmit={handleResubmit} />`; on submit calls `updateTask({ taskId: id, body: { ...updates, status: "pending" } })`; on success redirects to `/tasks`; add Edit button to `web/src/components/tasks/TaskTable.tsx` Actions column for tasks with `status === "aborted"` that links to `/tasks/{id}/edit`

**Checkpoint**: Aborted tasks have Edit button. Form pre-populated. Resubmit returns task to pending with updated values. US4 independently testable.

---

## Phase 7: User Story 5 — Configure System Settings (Priority: P5)

**Goal**: The Settings page shows the General tab with the `agent.work.path` field. The user can update and save the value. Settings persist across page reloads.

**Independent Test**: Navigate to `/settings`. Verify General tab is shown with `agent.work.path` field. Enter a path, click Save. Reload the page. Verify the saved path is still displayed.

> **⚠️ Write tests FIRST. Run them. Confirm they FAIL before writing any implementation.**

- [x] T039 [P] [US5] Write failing unit tests for `setting_service` in `api/tests/unit/test_setting_service.py`: test `get_settings(db)` returns `{"agent.work.path": ""}` when table is empty (default); test `get_settings(db)` returns persisted value when row exists; test `upsert_settings(db, {"agent.work.path": "/tmp"})` inserts on first call; test subsequent call updates the value; test `upsert_settings` with unknown key raises 422; use `db_session` fixture
- [x] T040 [US5] Write failing integration tests for `GET /settings` and `PUT /settings` in `api/tests/integration/test_settings_api.py`: test GET returns 200 with `{"settings": {"agent.work.path": ""}}` when no rows exist; test PUT with valid key returns 200 with updated value; test subsequent GET returns the previously saved value; test PUT with unknown key returns 422
- [x] T041 [US5] Create `api/src/api/services/setting_service.py`: define `ALLOWED_KEYS = {"agent.work.path"}` and `DEFAULTS = {"agent.work.path": ""}`; `async def get_settings(db)` → SELECT all from settings, merge with DEFAULTS for any missing keys, return dict; `async def upsert_settings(db, updates: dict[str, str])` → validate all keys are in ALLOWED_KEYS (raise 422 otherwise), INSERT … ON CONFLICT DO UPDATE for each key; unit tests must pass
- [x] T042 [US5] Implement `GET /settings` and `PUT /settings` in `api/src/api/routes/settings.py`: replace 501 stubs with real calls to `setting_service`; inject `db: AsyncSession = Depends(get_db)`; return `SettingsResponse`; integration tests must pass
- [x] T043 [P] [US5] Write failing `web/tests/unit/GeneralSettings.test.tsx`: test form renders an input for `agent.work.path` with label "Agent Working Directory"; test Save button is disabled when value is unchanged from initial; test Save button enabled when value changes; test `onSave` callback called with updated value on submit; test success message shown after save; test Cancel reverts unsaved changes
- [x] T044 [US5] Create `web/src/components/settings/GeneralSettings.tsx`: client component; props: `initialSettings: Record<string, string>`, `onSave: (settings: Record<string, string>) => Promise<void>`; renders shadcn/ui `Input` for `agent.work.path` labelled "Agent Working Directory" with a helper text "Working directory used by the agent"; Save button (disabled until value changes from initial); Cancel button (reverts to initial); shows success toast on save; all `GeneralSettings` unit tests must pass
- [x] T045 [US5] Create `web/src/app/settings/page.tsx`: server component; fetches settings via generated client `getSettings()`; renders page heading "Settings"; renders shadcn/ui `Tabs` with one tab "General" containing `<GeneralSettings initialSettings={settings.settings} onSave={handleSave} />`; `handleSave` calls `updateSettings()` from generated client

**Checkpoint**: `/settings` page persists `agent.work.path` across reloads. US5 independently testable.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: UI quality, accessibility, and code quality validation across all stories.

- [x] T046 [P] Create `web/src/components/tasks/StatusBadge.tsx`: renders task status as a coloured badge using Tailwind classes (pending=blue, aborted=yellow, in_progress=purple, completed=green, failed=red); integrate into `web/src/components/tasks/TaskTable.tsx` Status column replacing plain text
- [x] T047 [P] Add loading and error states to all pages: add `loading.tsx` files for `web/src/app/tasks/` and `web/src/app/settings/` (Next.js Suspense loading UI); add error display to `TaskForm.tsx` and `GeneralSettings.tsx` when API calls fail (show error message near Submit/Save button)
- [x] T048 [P] Add empty state component: create `web/src/components/tasks/EmptyState.tsx` with a message and "Submit your first task" link; use in `TaskTable.tsx` when `tasks.length === 0`; use a separate message "No tasks match your search" when search is active but returns no results
- [x] T049 Run `make test-all` from repo root; fix any failing unit, integration, or e2e tests until all pass
- [x] T050 [P] Run `ruff check api/src/ && ruff format --check api/src/` from repo root; fix all linting and formatting issues in `api/src/api/`
- [x] T051 [P] Run `cd web && npx tsc --noEmit`; fix all TypeScript type errors in `web/src/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001 before UI work; T002 before DB work) — **BLOCKS all user stories**
- **User Stories (Phases 3–7)**: All depend on Foundational phase completion; can proceed in priority order P1→P5
- **Polish (Phase 8)**: Depends on all user stories being complete

### Within Phase 2 (ordering)

1. T003–T007 (parallel) — models + schemas
2. T008–T010 (parallel with each other, after T003–T007) — stub routes using schemas
3. T011 — register routes in main.py
4. T012 — export spec + generate client (after T011)
5. T013 (parallel with T003–T012, depends only on T001) — frontend navigation shell

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on other stories
- **US2 (P2)**: Can start after Phase 2 — US1 data is useful for testing but not required
- **US3 (P3)**: Depends on US2 (adds Abort action to TaskTable built in US2)
- **US4 (P4)**: Depends on US2 (adds Edit action to TaskTable built in US2); US3 not required
- **US5 (P5)**: Fully independent — can start after Phase 2

### Within Each User Story

1. Failing tests (RED) — write and confirm failure before implementation
2. Service layer (GREEN) — make unit tests pass
3. Route layer (GREEN) — make integration tests pass
4. Frontend component tests (RED) — write and confirm failure
5. Frontend component implementation (GREEN) — make component tests pass
6. Frontend page (wires component to API)

---

## Parallel Execution Examples

### Phase 2 (first batch — parallel)
```
T003: Create Setting model        → api/src/api/models/setting.py
T004: Update db.py imports        → api/src/api/db.py
T005: Create schemas/task.py      → api/src/api/schemas/task.py
T006: Create schemas/project.py   → api/src/api/schemas/project.py
T007: Create schemas/setting.py   → api/src/api/schemas/setting.py
```

### Phase 2 (second batch — parallel, after schemas)
```
T008: Stub tasks routes           → api/src/api/routes/tasks.py
T009: Update projects stub        → api/src/api/routes/projects.py
T010: Stub settings routes        → api/src/api/routes/settings.py
```

### US1 — parallel opportunities
```
T014: Unit tests: project_service → api/tests/unit/test_project_service.py
T015: Unit tests: task_service    → api/tests/unit/test_task_service.py
T017: Implement project_service   → api/src/api/services/project_service.py
T020: Frontend test: TaskForm     → web/tests/unit/TaskForm.test.tsx
```

### US5 — parallel opportunities
```
T039: Unit tests: setting_service → api/tests/unit/test_setting_service.py
T043: Frontend test: GeneralSettings → web/tests/unit/GeneralSettings.test.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (task submission)
4. **STOP and VALIDATE**: `POST /tasks` returns correct response; `/tasks/new` form works end-to-end
5. Demo/deploy MVP

### Incremental Delivery

1. Setup + Foundational → API skeleton with correct schemas, navigation shell
2. US1 → Task submission working → MVP!
3. US2 → Task list with search → Users can see all submitted tasks
4. US3 → Abort action → Users can cancel pending tasks
5. US4 → Edit aborted tasks → Users can correct and requeue
6. US5 → Settings → Users can configure agent working directory
7. Polish → Quality gates pass, empty states, loading states

---

## Notes

- [P] tasks = different files, no mutual dependencies within the same phase
- TDD is non-negotiable: every failing test must be confirmed to fail before the implementation task starts
- API route stubs (T008–T010) exist only to export correct OpenAPI shapes — do not add business logic there
- Run `make generate` (T012) exactly once; re-run only if API schemas change
- Do not hand-edit `web/src/client/` — regenerate via `make generate`
- Commit after each phase checkpoint at minimum; prefer one commit per task
- Stop at any phase checkpoint to validate the story independently
