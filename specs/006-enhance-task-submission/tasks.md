# Tasks: Enhanced Task Submission

**Input**: Design documents from `/specs/006-enhance-task-submission/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/api.yaml ✓, quickstart.md ✓

**Tests**: Included — Constitution Principle II (TDD) is NON-NEGOTIABLE. Test tasks must be executed FIRST and must FAIL before implementation begins.

**Organization**: Tasks grouped by user story; each story is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on sibling tasks)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

---

## Phase 1: Setup (API-First per Constitution Principle VI)

**Purpose**: Update the OpenAPI contract and regenerate the TypeScript client before any implementation. This must complete before any business logic is written.

- [X] T001 Update `openapi.json` at repo root to version 0.3.0 — add `GET /agents` path; add schemas `AgentSummary`, `AgentResponse`, `PushTaskRequest`; update `CreateTaskRequest` (add required `agent_id: uuid`, optional `project_name: str | null`, make `dev_agent_type`/`test_agent_type` optional with `"deprecated": true`); update `POST /tasks/{task_id}/push` to add optional `requestBody` with `PushTaskRequest | null`; update `ProjectSummary` to include optional `git_url: string | null` and `created_at: string | null`; update `TaskResponse` and `TaskDetailResponse` to add `agent: AgentSummary | null` and mark `dev_agent_type`/`test_agent_type` as deprecated; bump `info.version` to `"0.3.0"`. Reference `specs/006-enhance-task-submission/contracts/api.yaml` as the authoritative target.
- [X] T002 Run `task generate` from repo root to regenerate `web/src/client/` TypeScript client from the updated `openapi.json`. Verify the generated types include `AgentSummary`, `AgentResponse`, `PushTaskRequest`, and `listAgents` SDK function.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: DB migrations and shared ORM/schema types that every user story requires.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Write Alembic migration `api/alembic/versions/0005_add_agents_table.py` — `revision="0005"`, `down_revision="0004"`. In `upgrade()`: call `op.create_table("agents", ...)` with columns `id` (postgresql.UUID, server_default gen_random_uuid(), PK), `identifier` (String(100), NOT NULL, UNIQUE), `display_name` (String(255), NOT NULL), `is_active` (Boolean, NOT NULL, server_default="true"), `created_at` (DateTime(timezone=True), server_default=now()). Then call `op.bulk_insert(agents_table, [{"identifier": "spec_driven_development", "display_name": "Spec-Driven Development", "is_active": True}, {"identifier": "generic_testing", "display_name": "Generic Testing", "is_active": True}])`. In `downgrade()`: `op.drop_table("agents")`.
- [X] T004 Write Alembic migration `api/alembic/versions/0006_add_agent_id_to_jobs.py` — `revision="0006"`, `down_revision="0005"`. In `upgrade()`: `op.add_column("jobs", sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True))` then `op.create_foreign_key("fk_jobs_agent_id", "jobs", "agents", ["agent_id"], ["id"])`. In `downgrade()`: `op.drop_constraint("fk_jobs_agent_id", "jobs", type_="foreignkey")` then `op.drop_column("jobs", "agent_id")`.
- [X] T005 [P] Create Agent ORM model in `api/src/api/models/agent.py` — class `Agent(Base)` with `__tablename__ = "agents"`. Fields: `id: Mapped[uuid.UUID]` (UUID(as_uuid=True), PK, default=uuid.uuid4, server_default=func.gen_random_uuid()), `identifier: Mapped[str]` (String(100), NOT NULL, unique=True), `display_name: Mapped[str]` (String(255), NOT NULL), `is_active: Mapped[bool]` (Boolean, NOT NULL, default=True, server_default="true"), `created_at: Mapped[datetime]` (DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()). Import `Base` from `api.models.project`. Follow exact conventions from `api/src/api/models/project.py`.
- [X] T006 [P] Create Agent Pydantic schemas in `api/src/api/schemas/agent.py` — `AgentSummary(BaseModel)` with fields `id: uuid.UUID`, `identifier: str`, `display_name: str` and `model_config = {"from_attributes": True}`. `AgentResponse(BaseModel)` with all `AgentSummary` fields plus `is_active: bool`, `created_at: datetime` and same model_config.
- [X] T007 Add `from api.models.agent import Agent  # noqa: F401` import to `api/src/api/db.py` after the existing model imports so SQLAlchemy registers the `agents` table metadata (required for Alembic autogenerate and for tests that create the DB schema from metadata).

**Checkpoint**: Run `docker compose -f compose.yaml -f compose.dev.yaml exec api alembic upgrade head` and verify migrations 0005 and 0006 apply cleanly. Confirm `agents` table exists with two seeded rows.

---

## Phase 3: User Story 1 — Submit Task for a New Project (Priority: P1) 🎯 MVP

**Goal**: User selects "New Project", enters a project name (required), optionally enters a git URL, selects a single agent from the DB-backed registry, enters requirements, and submits. System creates a new project with the given name and queues a pending task linked to the selected agent.

**Independent Test**: `POST /tasks` with `{"project_type":"new","project_name":"My App","agent_id":"<valid-uuid>","requirements":"Build something"}` returns 201 with `project.name = "My App"` and `agent.identifier = "<agent-identifier>"`.

### Tests for User Story 1 (write FIRST — verify they FAIL before implementing)

- [X] T008 [P] [US1] Write integration test `test_list_agents` in `api/tests/integration/test_agents.py` — fixture creates two `Agent` rows (one active, one with `is_active=False`); calls `GET /agents`; asserts 200, only active agent returned, ordered by `display_name`.
- [X] T009 [P] [US1] Write integration test `test_create_task_new_project_with_agent` in `api/tests/integration/test_create_task_agent.py` — fixture seeds one active `Agent`; posts `{"project_type":"new","project_name":"Acme","agent_id":"<seeded-id>","requirements":"Build it"}`; asserts 201, `project.name == "Acme"`, `agent.identifier == <seeded-identifier>`, `status == "pending"`.
- [X] T010 [P] [US1] Write integration test `test_create_task_new_project_missing_name` in `api/tests/integration/test_create_task_agent.py` — posts `{"project_type":"new","agent_id":"<valid-id>","requirements":"..."}`; asserts 422 with a field-level error mentioning `project_name`.
- [X] T011 [P] [US1] Write integration test `test_create_task_missing_agent_id` in `api/tests/integration/test_create_task_agent.py` — posts `{"project_type":"new","project_name":"X","requirements":"..."}`; asserts 422 with an error mentioning `agent_id`.

### Implementation for User Story 1

- [X] T012 [P] [US1] Implement `GET /agents` route in `api/src/api/routes/agents.py` — `router = APIRouter(prefix="/agents", tags=["agents"])`. Endpoint `list_agents(db)`: execute `select(Agent).where(Agent.is_active == True).order_by(Agent.display_name)`, return `list[AgentResponse]` using `AgentResponse.model_validate(a)`. Import `Agent` from `api.models.agent` and `AgentResponse` from `api.schemas.agent`.
- [X] T013 [P] [US1] Update `CreateTaskRequest` in `api/src/api/schemas/task.py` — add `agent_id: uuid.UUID` (required), add `project_name: str | None = None`. Change `dev_agent_type` and `test_agent_type` to use `Field(deprecated=True, default=DevAgentType.spec_driven_development)` / `Field(deprecated=True, default=TestAgentType.generic_testing)` so they are optional. Add `@model_validator(mode="after")` that raises `ValueError` if `project_type == ProjectType.new` and `project_name` is None or empty string. Use Pydantic v2 `model_validator`.
- [X] T014 [US1] Update `task_service.create_task` in `api/src/api/services/task_service.py` — when `project_type == "new"`: set `project.name = req.project_name`; when `req.git_url` is not None set `project.git_url = req.git_url`. When building the `Job`, set `agent_id=req.agent_id`; keep setting `dev_agent_type` and `test_agent_type` from their (now-defaulted) values for backward compat. Also update `api/src/api/models/job.py` to add `agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)` to the `Job` class.
- [X] T015 [US1] Update `task_service.list_tasks` and `task_service.get_task_detail` in `api/src/api/services/task_service.py` to LEFT JOIN the `agents` table: `select(Job, Project, Agent).outerjoin(Agent, Job.agent_id == Agent.id).join(Project, ...)`. `list_tasks` returns `list[tuple[Job, Project, Agent | None]]`. `get_task_detail` returns `tuple[Job, Project, WorkDirectory | None, Agent | None] | None`. Import `Agent` from `api.models.agent`.
- [X] T016 [US1] Update `_task_to_response` and `_task_to_detail_response` in `api/src/api/routes/tasks.py` to accept `agent: Agent | None` as a new parameter. Populate `agent=AgentSummary.model_validate(agent) if agent else None` in the response. Update all callers (`list_tasks`, `create_task` handler, `get_task_detail` handler, `update_task` handler) to unpack the new tuple element and pass `agent` to the helper. Import `AgentSummary` from `api.schemas.agent` and `Agent` from `api.models.agent`. Also update `TaskResponse` and `TaskDetailResponse` in `api/src/api/schemas/task.py` to add `agent: AgentSummary | None = None` field.
- [X] T017 [US1] Register the agents router in `api/src/api/main.py` — add `from api.routes.agents import router as agents_router` and `app.include_router(agents_router)` alongside the existing router registrations.
- [X] T018 [US1] Update `TaskForm.tsx` in `web/src/components/tasks/TaskForm.tsx` — (a) Add `agents: AgentResponse[]` to `TaskFormProps`. (b) Add `agent_id: string`, `project_name: string`, `git_url: string` fields to `TaskFormValues` interface; remove `dev_agent_type` and `test_agent_type`. (c) Replace the "Dev Agent" and "Test Agent" `<Select>` blocks with a single "Agent" `<Select>` populated from the `agents` prop (each `<SelectItem value={a.id}>{a.display_name}</SelectItem>`). (d) Add a "Project Name" `<Input>` field that is visible only when `projectSelect === "new"`; required. (e) Add a "Git URL" `<Input>` field that is always visible; optional for new projects. (f) Update `isFormValid` to also require `agent_id` is selected and `project_name` is non-empty when project is new. (g) Update `handleSubmit` to build the correct `TaskFormValues` shape.
- [X] T019 [US1] Update `web/src/app/tasks/new/page.tsx` — (a) Add `agents` state: `const [agents, setAgents] = useState<AgentResponse[]>([])`. (b) In `useEffect`, call `listAgents()` (generated SDK function) and populate `agents`. (c) Pass `agents={agents}` to `<TaskForm>`. (d) Update `handleSubmit`'s `createTaskTasksPost` body to send `agent_id: data.agent_id`, `project_name: data.project_name ?? undefined`, `git_url: data.git_url || undefined`; remove the hardcoded `dev_agent_type`/`test_agent_type` casts.

**Checkpoint**: Run `docker compose exec api pytest tests/integration/test_agents.py tests/integration/test_create_task_agent.py -v` — all 4 tests pass. Open the web form: "New Project" shows Project Name + optional Git URL fields; Agent dropdown lists registry agents. Submit a task and verify it appears in the task list with the agent name.

---

## Phase 4: User Story 2 — Submit Task for an Existing Project (Priority: P2)

**Goal**: User selects an existing project from the dropdown, sees its stored git URL pre-populated in a required field, selects an agent, enters requirements, and submits. System validates the git URL is present and links the task to the existing project.

**Independent Test**: Seed a project with `git_url="https://github.com/org/repo"`. `POST /tasks` with `{"project_type":"existing","project_id":"<id>","git_url":"https://github.com/org/repo","agent_id":"<id>","requirements":"..."}` returns 201 linked to the existing project.

### Tests for User Story 2 (write FIRST — verify they FAIL before implementing)

- [X] T020 [P] [US2] Write integration test `test_create_task_existing_project_with_git_url` in `api/tests/integration/test_create_task_existing.py` — fixture seeds a project with `git_url` and an active agent; posts existing-project task with all fields; asserts 201, task linked to correct project.
- [X] T021 [P] [US2] Write integration test `test_create_task_existing_project_missing_git_url` in `api/tests/integration/test_create_task_existing.py` — posts existing-project task with `project_id` but no `git_url`; asserts 422 with an error mentioning `git_url`.

### Implementation for User Story 2

- [X] T022 [US2] Extend the `@model_validator(mode="after")` in `CreateTaskRequest` in `api/src/api/schemas/task.py` to add a second rule: if `project_type == ProjectType.existing` then `project_id` must not be None AND `git_url` must be a non-empty string. Raise a `ValueError` with a message like "git_url is required for existing projects" if either condition fails.
- [X] T023 [US2] Update `task_service.create_task` in `api/src/api/services/task_service.py` — in the `else` (existing project) branch: after loading the project, if `req.git_url` is not None, set `project.git_url = req.git_url` and call `await db.flush()` to persist the update before creating the job.
- [X] T024 [US2] Update `GET /projects` to include `git_url` and `created_at` in the response — in `api/src/api/routes/projects.py`, change the response schema from `ProjectSummary` to `ProjectSummaryWithGitUrl` (already defined in `api/src/api/schemas/task.py`). Verify `ProjectSummaryWithGitUrl` has `git_url` and `created_at` fields (add `created_at: datetime | None = None` if missing). Update `openapi.json` path `/projects` GET response to reference `ProjectSummaryWithGitUrl` schema.
- [X] T025 [US2] Update `TaskForm.tsx` in `web/src/components/tasks/TaskForm.tsx` — (a) Change `projects` prop type from `ProjectSummary[]` to `ProjectSummaryWithGitUrl[]`. (b) When the user selects an existing project (non-"new" value), find the matching project in the `projects` array and pre-populate the `gitUrl` state with `project.git_url ?? ""`. (c) Mark the Git URL field as required when `projectSelect !== "new"` (add `required` attribute and red asterisk). (d) Validate in `isFormValid`: when existing project, `gitUrl` must be non-empty. (e) Include `git_url: gitUrl || undefined` in the form submit data.

**Checkpoint**: Run `docker compose exec api pytest tests/integration/test_create_task_existing.py -v`. Verify both tests pass. In the web form: selecting an existing project with a stored URL pre-populates the Git URL field; submitting without a URL is blocked with an inline error.

---

## Phase 5: User Story 3 — Add Git URL and Push (Priority: P3)

**Goal**: On a completed new-project task's detail page, users can enter a git URL (if not already stored), click "Push to Remote", and the system saves the URL to the project and pushes the work directory to that repository. If the project already has a URL, it is pre-filled.

**Independent Test**: Seed a completed task for a new project with no `git_url`. `POST /tasks/{id}/push` with body `{"git_url":"https://github.com/org/repo"}` returns 200 PushResponse and the project's `git_url` is now saved.

### Tests for User Story 3 (write FIRST — verify they FAIL before implementing)

- [X] T026 [P] [US3] Write integration test `test_push_with_git_url_body` in `api/tests/integration/test_push_with_git_url.py` — fixture seeds a completed job with a work directory and project with no `git_url`; posts `{"git_url":"https://github.com/org/repo"}` to `/tasks/{id}/push` with git operations mocked; asserts 200 and project `git_url` is updated in the DB.
- [X] T027 [P] [US3] Write integration test `test_push_without_body_uses_stored_url` in `api/tests/integration/test_push_with_git_url.py` — fixture seeds a completed job with a project that has `git_url` set; posts `/tasks/{id}/push` with no body; asserts 200 using the stored URL (git operations mocked).

### Implementation for User Story 3

- [X] T028 [P] [US3] Add `PushTaskRequest(BaseModel)` to `api/src/api/schemas/task.py` with field `git_url: str | None = None` and `model_config = {"from_attributes": True}`. This schema is already referenced in `openapi.json` (from T001); this task adds the Python implementation.
- [X] T029 [US3] Update `push_task_to_remote` endpoint in `api/src/api/routes/tasks.py` — change signature to `async def push_task_to_remote(task_id: uuid.UUID, body: Annotated[PushTaskRequest | None, Body()] = None, db: AsyncSession = Depends(get_db))`. Extract `git_url_override = body.git_url if body else None` and pass to service. Import `Annotated` from `typing` and `Body` from `fastapi`. Import `PushTaskRequest` from `api.schemas.task`.
- [X] T030 [US3] Update `task_service.trigger_push` in `api/src/api/services/task_service.py` — add parameter `git_url_override: str | None = None`. Inside the function: after loading the task and project, if `git_url_override` is not None, set `project.git_url = git_url_override` and `await db.flush()` to persist before pushing. Change `effective_git_url = git_url_override or project.git_url`. Use `effective_git_url` as the push target. Raise 422 if `effective_git_url` is None.
- [X] T031 [US3] Update `PushToRemoteButton.tsx` in `web/src/components/tasks/PushToRemoteButton.tsx` — (a) Add `projectGitUrl: string | null | undefined` to `PushToRemoteButtonProps`. (b) Add `gitUrl` state initialized from `projectGitUrl`. (c) Before the push button, when `projectGitUrl` is null/empty, show an `<Input>` field labelled "Git Repository URL" with `value={gitUrl}` and `onChange`; include inline validation for `https://` or `git@` prefix. (d) In `handlePush`: pass `body: { git_url: gitUrl || undefined }` to `pushTaskToRemote`. (e) Disable the push button if git URL is empty (neither stored nor entered) or if URL format is invalid.
- [X] T032 [US3] Update `web/src/app/tasks/[id]/page.tsx` — pass `projectGitUrl={task.project.git_url}` prop to `<PushToRemoteButton>`.

**Checkpoint**: Run `docker compose exec api pytest tests/integration/test_push_with_git_url.py -v`. Verify both tests pass. In the web UI: on a completed task for a new project with no URL, the push section shows a Git URL input; entering a valid URL enables the Push button; after pushing, the URL is stored and the success message shown.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Linting, type safety, and final validation.

- [X] T033 [P] Run `ruff check src/` from `api/` and fix any linting errors introduced by this feature's changes. Focus on new files: `api/src/api/models/agent.py`, `api/src/api/routes/agents.py`, `api/src/api/schemas/agent.py`.
- [X] T034 [P] Run `npx tsc --noEmit` from `web/` and fix any TypeScript type errors introduced by the updated client types and modified components (`TaskForm.tsx`, `PushToRemoteButton.tsx`, `tasks/new/page.tsx`, `tasks/[id]/page.tsx`).
- [X] T035 Run `task e2e` from repo root and verify the full end-to-end test suite still passes. Manually validate the three quickstart.md scenarios against the running dev stack (`task dev`): (1) submit new project task with agent, (2) submit existing project task with git URL, (3) push completed task with entered URL.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start here.
- **Phase 2 (Foundational)**: Depends on Phase 1 (T002 must complete so TypeScript types are available).
- **Phase 3 (US1)**: Depends on Phase 2 completion — all foundational DB and schema work must be in place.
- **Phase 4 (US2)**: Depends on Phase 2 completion — can start in parallel with US1 if staffed, but US1's `@model_validator` for `project_type="new"` should be complete first (T013) since T022 extends it.
- **Phase 5 (US3)**: Depends on Phase 2 completion — can start in parallel with US1/US2.
- **Phase 6 (Polish)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Must complete after Phase 2. No dependency on US2/US3.
- **US2 (P2)**: Must complete after Phase 2. T022 extends T013's `@model_validator` (edit same file sequentially). T023 extends T014's `create_task` (edit same file sequentially).
- **US3 (P3)**: Must complete after Phase 2. T028 adds to same schema file as T013/T022 (sequential). T029-T030 extend the push endpoint (independent of US1/US2 task creation logic).

### Within Each User Story

- Tests (T008-T011, T020-T021, T026-T027) MUST be written first and verified to FAIL.
- Models/schemas (T005-T006, T012-T013, T028) before service layer tasks.
- Service layer (T014-T015, T022-T023, T030) before route layer tasks.
- Route/endpoint tasks (T016, T029) before web/frontend tasks.
- Frontend tasks (T018, T019, T025, T031-T032) last in each story.

### Parallel Opportunities

Within Phase 3 (US1):
- T008, T009, T010, T011 — all test tasks can run in parallel (write simultaneously)
- T012, T013 — can run in parallel (different files: routes/agents.py vs schemas/task.py)
- T014 must follow T013; T015 can run in parallel with T014
- T016 must follow T015; T017 can run in parallel with T016
- T018 and T019 can run in parallel (different files)

Within Phase 4 (US2):
- T020 and T021 — test tasks can run in parallel
- T022 must follow T013 (extends same validator)

---

## Parallel Example: User Story 1

```bash
# Step 1 — Write tests (can all be started together):
T008: test_agents.py                  # GET /agents tests
T009: test_create_task_agent.py       # New project + agent_id tests
T010: test_create_task_agent.py       # Missing project_name test
T011: test_create_task_agent.py       # Missing agent_id test

# Step 2 — Core implementation (parallel where [P] marked):
T012: routes/agents.py                # New GET /agents endpoint
T013: schemas/task.py                 # Updated CreateTaskRequest

# Step 3 — Service layer (sequential within service, independent of routes):
T014: task_service.py (create_task)   # After T013
T015: task_service.py (list/detail)   # Can run with T014

# Step 4 — Route integration (after T015):
T016: routes/tasks.py                 # Agent field in responses
T017: main.py                         # Router registration

# Step 5 — Frontend (parallel with each other, after T016):
T018: TaskForm.tsx                    # Form changes
T019: tasks/new/page.tsx              # Page data fetching
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (T001-T002): OpenAPI + client generation
2. Complete Phase 2 (T003-T007): Migrations + Agent model
3. Complete Phase 3 (T008-T019): US1 full implementation
4. **STOP and VALIDATE**: All US1 tests pass; web form works end-to-end
5. Deploy/demo the MVP

### Incremental Delivery

1. Phase 1 + Phase 2 → shared foundation ready
2. Phase 3 (US1) → new project flow complete → validate → demo
3. Phase 4 (US2) → existing project flow complete → validate → demo
4. Phase 5 (US3) → push with URL complete → validate → demo
5. Phase 6 (Polish) → lint, types, e2e → ready for merge

---

## Notes

- `[P]` tasks touch different files and have no blocking dependencies on sibling tasks.
- TDD is non-negotiable (Constitution Principle II): write tests, confirm they FAIL, then implement.
- The `@model_validator` in `CreateTaskRequest` handles all cross-field rules (project_name required for new, git_url required for existing). US1 adds the first rule; US2 adds the second rule in T022.
- The `agent` field in task responses is `null` for legacy tasks (no `agent_id`). This is intentional and documented.
- After US3 implementation, the push button in the web UI conditionally shows a URL input — this is an in-place enhancement to `PushToRemoteButton.tsx`.
- All file paths are relative to the repository root at `D:/workspace/github/wliant/coding-server/`.
