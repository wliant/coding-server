# Tasks: Automated Task Execution via Agent Worker

**Input**: Design documents from `/specs/005-requirements-feature/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/api.yaml ✅ quickstart.md ✅

**Tests**: Included — constitution principle II (TDD) is NON-NEGOTIABLE. Test tasks MUST be written and confirmed failing before their corresponding implementation tasks.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P]-marked tasks in the same phase
- **[Story]**: User story this task belongs to (US1, US2, US3)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (API Contract & Client)

**Purpose**: Establish the API contract before any implementation. Per constitution principle VI, the OpenAPI spec MUST be the first implementation artifact.

**⚠️ CRITICAL**: T002 must complete before any frontend work begins.

- [X] T001 Update `openapi.json` with new endpoints and schemas from `specs/005-requirements-feature/contracts/api.yaml` — add `GET /tasks/{task_id}`, `POST /tasks/{task_id}/push`, extend `CreateTaskRequest` with `git_url`, add `TaskDetailResponse`, `PushResponse`, `ProjectSummaryWithGitUrl` schemas; bump `info.version` to `0.2.0`
- [X] T002 Run `task generate` to regenerate TypeScript client in `web/src/client/` from updated `openapi.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema extension, model updates, and config changes that ALL user stories depend on. Must complete before any user story implementation.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Write Alembic migration `api/alembic/versions/0004_add_job_lease_fields.py` — adds `lease_holder VARCHAR(36) NULLABLE` and `lease_expires_at TIMESTAMPTZ NULLABLE` to `jobs` table; downgrade drops both columns
- [X] T004 Extend `Job` model in `api/src/api/models/job.py` — add `lease_holder: Mapped[str | None] = mapped_column(String(36), nullable=True)` and `lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)`
- [X] T005 [P] Extend `worker/src/worker/config.py` `Settings` class — add `POLL_INTERVAL_SECONDS: int = 5`, `LEASE_TTL_SECONDS: int = 300`, `LEASE_RENEWAL_INTERVAL_SECONDS: int = 120`, `LLM_PROVIDER: str = "ollama"`, `LLM_MODEL: str = "qwen2.5-coder:7b"`, `LLM_TEMPERATURE: float = 0.2`, `OLLAMA_BASE_URL: str = "http://localhost:11434"`, `OPENAI_API_KEY: str = "NA"`, `ANTHROPIC_API_KEY: str = ""`
- [X] T006 [P] Add `git_url: str | None = None` field to `CreateTaskRequest` in `api/src/api/schemas/task.py`
- [X] T007 Update `task_service.create_task()` in `api/src/api/services/task_service.py` — when `project_type == "new"`, store the `git_url` value from the request in `Project.git_url`

**Checkpoint**: Database migration applied, models updated, config extended, git_url flows into new projects. User story implementation can now begin.

---

## Phase 3: User Story 1 — Worker Picks Up and Executes a Pending Task (Priority: P1) 🎯 MVP

**Goal**: The worker automatically detects Pending tasks, acquires a lease, invokes `simple_crewai_pair_agent.CodingAgent`, writes code to an isolated working directory, and transitions the task to Completed or Failed.

**Independent Test**: Submit a task via the existing POST /tasks endpoint, start the worker, and verify: (1) task transitions to In Progress within 10 s, (2) `work_directories` row is created with path `{AGENT_WORK_PARENT}/{job_id}`, (3) task transitions to Completed with code present in the working directory, or Failed with a non-empty `error_message`.

### Tests for User Story 1 — Write FIRST, confirm FAILING before implementing

- [X] T008 [P] [US1] Write failing unit tests for `acquire_lease()`, `renew_lease()`, `release_lease()`, and `reap_expired_leases()` in `worker/tests/unit/test_lease_manager.py` — cover: successful claim sets status/lease_holder/lease_expires_at; failed claim (race) returns None; reaper resets expired In Progress rows to Pending; release clears lease fields
- [X] T009 [P] [US1] Write failing unit tests for `run_coding_agent()` in `worker/tests/unit/test_agent_runner.py` — cover: successful run creates WorkDirectory record and returns success result; agent exception returns error result with message; working directory path equals `{AGENT_WORK_PARENT}/{job_id}`
- [X] T010 [US1] Write failing integration test for full poll → claim → execute → complete cycle in `worker/tests/integration/test_worker_loop.py` — seed a Pending job, run one poll iteration, assert job is In Progress then Completed (or Failed) with WorkDirectory created

### Implementation for User Story 1

- [X] T011 [P] [US1] Create `worker/src/worker/lease_manager.py` — implement `acquire_lease(db, job_id, worker_id, ttl_seconds) -> bool` using atomic SQLAlchemy `update(Job).where(Job.id == job_id, Job.status == "pending").values(status="in_progress", lease_holder=worker_id, lease_expires_at=now+ttl, started_at=now)`; implement `renew_lease(db, job_id, worker_id, ttl_seconds)`; `release_lease(db, job_id)`; `reap_expired_leases(db)` that resets In Progress jobs with `lease_expires_at < now()` back to Pending
- [X] T012 [US1] Create `worker/src/worker/agent_runner.py` — implement `run_coding_agent(db, job, work_parent, settings) -> tuple[bool, str | None]`; derive `work_dir = Path(work_parent) / str(job.id)`; create `WorkDirectory` DB record; invoke `CodingAgent(CodingAgentConfig(...)).run()`; return `(True, None)` on success, `(False, error_message)` on exception
- [X] T013 [US1] Implement `main_loop()` in `worker/src/worker/worker.py` — replace skeleton with: (1) generate worker UUID on startup; (2) poll every `settings.POLL_INTERVAL_SECONDS` for Pending jobs; (3) attempt `acquire_lease`; (4) on success, start background `asyncio.Task` for lease renewal every `LEASE_RENEWAL_INTERVAL_SECONDS`; (5) call `run_coding_agent`; (6) cancel renewal task; (7) `release_lease` and update job to Completed or Failed with `completed_at`; (8) also call `reap_expired_leases` each poll cycle; emit structured log entries at each state transition (`task_claimed`, `task_completed`, `task_failed`, `lease_renewed`, `lease_reaped`)

**Checkpoint**: Worker fully functional. Submit a task, start the worker — task should execute and reach Completed or Failed status.

---

## Phase 4: User Story 2 — Task Status Reflects Worker Progress (Priority: P2)

**Goal**: A new `GET /tasks/{id}` API endpoint returns full task detail including status, elapsed time (when In Progress), working directory path, and error message. A new task detail web page renders this data.

**Independent Test**: Call `GET /tasks/{id}` for a task in each status (Pending, In Progress, Completed, Failed) and verify the response shape. Open the task detail page in the browser and verify it renders status, elapsed time (In Progress only), and error message (Failed only).

### Tests for User Story 2 — Write FIRST, confirm FAILING before implementing

- [X] T014 [P] [US2] Write failing unit tests for `get_task_detail()` in `api/tests/unit/test_task_service.py` — cover: returns job + project + work_directory data; `elapsed_seconds` is non-null only when status is `in_progress`; returns None for unknown task_id
- [X] T015 [P] [US2] Write failing integration tests for `GET /tasks/{id}` in `api/tests/integration/test_tasks_api.py` — cover: 200 with `TaskDetailResponse` shape for existing task; 404 for unknown UUID; `work_directory_path` is null before worker claims task

### Implementation for User Story 2

- [X] T016 [P] [US2] Add `TaskDetailResponse` schema to `api/src/api/schemas/task.py` — extends `TaskResponse` with `started_at: datetime | None`, `completed_at: datetime | None`, `work_directory_path: str | None`, `elapsed_seconds: int | None`; add `ProjectSummaryWithGitUrl` (adds `git_url: str | None` to existing `ProjectSummary`)
- [X] T017 [US2] Implement `get_task_detail(db, task_id) -> tuple[Job, Project, WorkDirectory | None] | None` in `api/src/api/services/task_service.py` — LEFT JOIN `work_directories`; raise 404 if job not found
- [X] T018 [US2] Add `GET /tasks/{task_id}` route to `api/src/api/routes/tasks.py` — calls `get_task_detail`, serialises to `TaskDetailResponse` computing `elapsed_seconds = int((now - job.started_at).total_seconds())` only when `status == "in_progress"`
- [X] T019 [P] [US2] Create `web/src/app/tasks/[id]/page.tsx` — fetch task detail via generated SDK `getTaskDetail({path: {task_id: id}})`; render: title, requirements, git URL, `StatusBadge`, elapsed time paragraph (In Progress only), error message alert (Failed only), working directory path, `PushToRemoteButton` placeholder (hidden until US3)
- [X] T020 [P] [US2] Create `web/src/app/tasks/[id]/loading.tsx` — skeleton layout matching detail page structure using shadcn/ui `Skeleton` components
- [X] T021 [US2] Update `web/src/components/tasks/TaskTable.tsx` — wrap each task row (or title cell) in a Next.js `<Link href={/tasks/${task.id}}>` to navigate to the detail page

**Checkpoint**: Task detail page accessible. Click any task in the list — opens detail page showing current status, elapsed time for In Progress, error for Failed.

---

## Phase 5: User Story 3 — Push Completed Task Changes to Remote Git (Priority: P3)

**Goal**: A `POST /tasks/{id}/push` endpoint force-pushes the task's working directory as branch `task/{job_id[:8]}` to `Project.git_url`. The task detail page exposes a Push to Remote button for Completed tasks.

**Independent Test**: Complete a task (or manually seed a WorkDirectory), call `POST /tasks/{id}/push`, and verify the named branch appears in the remote git repository. Triggering push a second time overwrites the same branch (force-push idempotency).

### Tests for User Story 3 — Write FIRST, confirm FAILING before implementing

- [X] T022 [P] [US3] Write failing unit tests for `push_working_directory_to_remote()` in `api/tests/unit/test_git_service.py` — mock `git.Repo`; cover: successful push returns `PushResponse` with correct `branch_name` and `remote_url`; git exception raises HTTP 502-mappable error; non-existent work dir raises appropriate error
- [X] T023 [P] [US3] Write failing integration tests for `POST /tasks/{id}/push` in `api/tests/integration/test_tasks_api.py` — cover: 409 when task is not Completed; 422 when project has no git_url; 404 for unknown task; 200 with `PushResponse` shape on success (mock git push)

### Implementation for User Story 3

- [X] T024 [US3] Add `gitpython` to `api/pyproject.toml` dependencies
- [X] T025 [P] [US3] Add `PushResponse` schema to `api/src/api/schemas/task.py` — fields: `branch_name: str`, `remote_url: str`, `pushed_at: datetime`
- [X] T026 [US3] Create `api/src/api/services/git_service.py` — implement `push_working_directory_to_remote(work_dir_path: str, remote_url: str, branch_name: str) -> PushResponse`; use `gitpython` to open repo at `work_dir_path` (init if no `.git`), create/reset branch, add all changes, commit if dirty, force-push to `remote_url`; emit structured log entries for push start and outcome
- [X] T027 [US3] Implement `trigger_push(db, task_id) -> PushResponse` in `api/src/api/services/task_service.py` — load task + project + work_directory; raise 409 if status != completed; raise 422 if project.git_url is None; construct `branch_name = f"task/{str(task_id)[:8]}"`; call `git_service.push_working_directory_to_remote()`
- [X] T028 [US3] Add `POST /tasks/{task_id}/push` route to `api/src/api/routes/tasks.py` — calls `trigger_push`; maps 409/422 to appropriate HTTP errors; wraps git errors in 502 response with human-readable detail
- [X] T029 [P] [US3] Create `web/src/components/tasks/PushToRemoteButton.tsx` — button that calls `pushTaskToRemote({path: {task_id}})` from generated SDK; shows spinner while loading; on success displays `"Pushed to branch {branch_name} → {remote_url}"`; on error displays error message; disabled after successful push
- [X] T030 [US3] Wire `PushToRemoteButton` into `web/src/app/tasks/[id]/page.tsx` — render `<PushToRemoteButton taskId={id} />` only when `task.status === "completed"`; remove the placeholder added in T019

**Checkpoint**: Full end-to-end flow working. Submit task → worker executes → open detail page → push to remote → verify branch in git repository.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Environment wiring, validation, and final checks.

- [X] T031 [P] Update `compose.dev.yaml` worker service — add all LLM env vars (`LLM_PROVIDER`, `LLM_MODEL`, `OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `POLL_INTERVAL_SECONDS`, `LEASE_TTL_SECONDS`, `LEASE_RENEWAL_INTERVAL_SECONDS`) with sensible dev defaults
- [X] T032 [P] Update `compose.yaml` (prod) worker service — add same LLM env var keys (values supplied at deploy time; defaults only for non-secret vars)
- [X] T033 Run end-to-end validation per `specs/005-requirements-feature/quickstart.md` — submit a task with a valid git URL, confirm worker picks it up, reaches Completed, push creates branch on remote; verify all acceptance scenarios from spec.md SC-001 through SC-005

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 (T001, T002 complete) — BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 complete — MVP deliverable
- **Phase 4 (US2)**: Depends on Phase 2 complete — can run in parallel with Phase 3
- **Phase 5 (US3)**: Depends on Phase 2 complete — depends on Phase 4 (detail page) for web integration
- **Phase 6 (Polish)**: Depends on all desired user stories complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational. No dependency on US2 or US3.
- **US2 (P2)**: Depends only on Foundational. No dependency on US1 (uses existing task data).
- **US3 (P3)**: Depends on US2 (detail page is the push action host). API portion independent of US2.

### Within Each User Story

- Test tasks MUST be written and FAILING before any implementation task in that story
- Models/schemas before services (T016 before T017)
- Services before routes (T017 before T018)
- Routes before frontend (T018 before T019)
- Core page before button integration (T019 before T030)

### Parallel Opportunities

- T005, T006 can run in parallel during Phase 2
- T008, T009 can run in parallel (different test files)
- T011 can run in parallel with T008/T009 (lease_manager.py is independent of agent_runner.py)
- T014, T015 can run in parallel (different concerns)
- T016, T019, T020 can run in parallel (different files)
- T022, T023 can run in parallel
- T024, T025, T029 can run in parallel
- T031, T032, T033 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch test scaffolding in parallel:
Task T008: worker/tests/unit/test_lease_manager.py   # lease logic
Task T009: worker/tests/unit/test_agent_runner.py    # agent invocation

# Launch implementation in parallel (after tests fail):
Task T011: worker/src/worker/lease_manager.py        # lease logic
# Then sequentially:
Task T012: worker/src/worker/agent_runner.py         # depends on lease_manager
Task T013: worker/src/worker/worker.py               # depends on both
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T007)
3. Complete Phase 3: User Story 1 (T008–T013)
4. **STOP and VALIDATE**: Submit task via existing UI, observe worker execution, check DB status transitions
5. Deploy/demo: Core value delivered — tasks now execute automatically

### Incremental Delivery

1. **Phase 1 + 2**: Foundation ready (migration, model, config, openapi updated)
2. **Phase 3 (US1)**: Worker executes tasks → Demo: task goes from Pending to Completed
3. **Phase 4 (US2)**: Task detail page → Demo: click task, see In Progress timer and results
4. **Phase 5 (US3)**: Git push → Demo: click Push, branch appears in remote repo
5. **Phase 6**: Polish, environment wiring, full e2e validation

---

## Notes

- Constitution Principle II (TDD) is NON-NEGOTIABLE: T008–T010 MUST fail before T011–T013; T014–T015 before T016–T021; T022–T023 before T024–T030
- `[P]` tasks operate on different files — safe to run in parallel with other `[P]` tasks in the same phase
- Each user story phase ends with a Checkpoint — validate independently before starting the next story
- Cross-spec dependency: T007 (storing git_url) is the spec 002 form extension wired in at the service layer; no spec 002 tasks are repeated here
- Commit after each task or logical group per constitution Principle V
