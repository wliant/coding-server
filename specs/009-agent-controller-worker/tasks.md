# Tasks: Agent Controller / Worker Redesign

**Input**: Design documents from `specs/009-agent-controller-worker/`
**Branch**: `009-agent-controller-worker`
**Constitution**: TDD required — tests MUST be written before implementation for each story.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: API-First compliance and project scaffolding. MUST complete before any story work.

- [X] T001 Update `openapi.json` — add `cleaning_up`/`cleaned` to TaskStatus enum; add `POST /tasks/{id}/cleanup` and `GET /workers` endpoints; add `CleanupResponse` and `WorkerStatus` schemas; add `assigned_worker_id` to TaskDetailResponse; bump version to `0.6.0`
- [X] T002 Create `controller/` directory structure: `pyproject.toml`, `Dockerfile`, `src/controller/__init__.py`, `tests/__init__.py`
- [X] T003 [P] Regenerate TypeScript client: `cd web && npm run generate` (after T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core DB changes and package scaffolding that all user stories depend on.

⚠️ **CRITICAL**: No story implementation can begin until this phase is complete.

- [X] T004 Create `api/alembic/versions/0009_add_worker_fields_to_jobs.py` — add `assigned_worker_id VARCHAR(255) NULL` and `assigned_worker_url VARCHAR(255) NULL` columns to `jobs` table
- [X] T005 Update `api/src/api/models/job.py` — add `assigned_worker_id: Mapped[str | None]` and `assigned_worker_url: Mapped[str | None]` mapped columns (after T004)
- [X] T006 Update `api/src/api/schemas/task.py` — add `cleaning_up` and `cleaned` to `TaskStatus` enum; add `CleanupResponse` and `WorkerStatus` Pydantic models; add `assigned_worker_id: str | None = None` to `TaskDetailResponse` (after T001)
- [X] T007 [P] Create `controller/src/controller/config.py` — pydantic-settings `Settings` class with `DATABASE_URL`, `API_URL`, `CONTROLLER_PORT`, `POLL_INTERVAL_SECONDS` (default 10), `HEARTBEAT_TIMEOUT_SECONDS` (default 60), `LEASE_TTL_SECONDS` (default 300)
- [X] T008 [P] Create `controller/src/controller/registry.py` — `WorkerRecord` dataclass and `WorkerRegistry` class with `asyncio.Lock`-protected `dict[str, WorkerRecord]`; methods: `register()`, `heartbeat()`, `get_all()`, `get_free_worker_for_agent_type()`, `mark_unreachable()`
- [X] T009 [P] Create `controller/src/controller/models.py` — SQLAlchemy async models for main DB: `Job` (read/write: status, lease fields, assigned_worker_id, assigned_worker_url), `Project` (read), `Agent` (read)
- [X] T010 [P] Update `worker/src/worker/config.py` — add `CONTROLLER_URL` (default `http://controller:8002`), `AGENT_TYPE` (required), `WORK_DIR` (default `/agent-work`), `HEARTBEAT_INTERVAL_SECONDS` (default 15); remove `AGENT_WORK_PARENT`, `POLL_INTERVAL_SECONDS`, `LEASE_TTL_SECONDS`, `LEASE_RENEWAL_INTERVAL_SECONDS`, `API_URL`
- [X] T011 [P] Create `worker/alembic/` setup with `env.py` and migration `worker_0001_create_worker_executions.py` — creates `worker_executions` table with columns: `id UUID PK`, `task_id UUID UNIQUE NOT NULL`, `agent_type VARCHAR(255) NOT NULL`, `status VARCHAR(50) NOT NULL`, `started_at TIMESTAMPTZ NOT NULL`, `completed_at TIMESTAMPTZ NULL`, `error_message TEXT NULL`, `work_dir_path VARCHAR(1024) NOT NULL`
- [X] T012 [P] Update `worker/src/worker/models.py` — replace old `Job`/`Project`/`WorkDirectory` models with `WorkExecution` model mapped to `worker_executions` table (after T011)
- [X] T013 Update `controller/pyproject.toml` — Python 3.12, dependencies: `fastapi>=0.115`, `uvicorn[standard]>=0.30`, `sqlalchemy[asyncio]>=2.0`, `asyncpg>=0.30`, `pydantic-settings>=2.0`, `python-json-logger>=2.0`, `httpx>=0.27`; dev deps: `pytest>=8.0`, `pytest-asyncio>=0.23`, `ruff>=0.4`, `aiosqlite>=0.20`; `asyncio_mode = "auto"`

**Checkpoint**: Foundation ready — all story phases can begin.

---

## Phase 3: User Story 1 — Worker Registration and Task Delegation (P1) 🎯 MVP

**Goal**: A worker registers with the Controller on startup and receives tasks that match its agent type. Controller polls DB and delegates pending tasks to free workers.

**Independent Test**: Start controller + one worker. Submit a task for the matching agent type. Confirm task transitions to `in_progress` and worker status shows `in_progress`.

### Tests for User Story 1 ⚠️ Write FIRST — confirm RED before implementing

- [X] T014 Write `controller/tests/test_registry.py` — unit tests for `WorkerRegistry`: register returns worker_id; duplicate worker_url replaces existing record; get_free_worker_for_agent_type returns None when none free; mark_unreachable sets status; heartbeat updates timestamp
- [X] T015 Write `controller/tests/test_routes.py` — tests for `POST /workers/register` (happy path, missing fields); `GET /health`; `GET /workers` (empty list, populated list); `POST /workers/{id}/heartbeat` (known worker updates timestamp, unknown worker 404)
- [X] T016 Write `controller/tests/test_delegator.py` — unit tests for delegation logic: pending job with matching free worker is claimed (DB UPDATE verified); if no free worker, job stays pending; if worker /work call fails, DB claim is rolled back to pending
- [X] T017 Write `worker/tests/test_registration.py` — unit tests for `register_with_controller()`: successful registration returns worker_id; retries on ConnectionError; heartbeat loop calls controller heartbeat endpoint with correct payload

### Implementation for User Story 1

- [X] T018 Implement `controller/src/controller/routes.py` — FastAPI router with `POST /workers/register`, `POST /workers/{worker_id}/heartbeat`, `GET /health`, `GET /workers` (returns list from registry) (after T014, T015)
- [X] T019 Implement `controller/src/controller/delegator.py` — async polling loop with `POLL_INTERVAL_SECONDS` sleep; `_delegate_pending_tasks()`: query DB for pending jobs (joined with agents), match agent name to free worker, atomically UPDATE job (status=in_progress, lease fields, assigned_worker_id, assigned_worker_url), POST to worker `/work` with task payload; rollback on worker call failure (after T016)
- [X] T020 Implement `controller/src/controller/app.py` — FastAPI app with lifespan: start delegator loop as background task; include routes from T018; configure structured JSON logging (after T018, T019)
- [X] T021 Create `controller/Dockerfile` — Python 3.12-slim base; install controller package; `CMD ["uvicorn", "controller.app:app", "--host", "0.0.0.0", "--port", "8002"]`
- [X] T022 Implement `worker/src/worker/registration.py` — `register_with_controller(config)` calls `POST {CONTROLLER_URL}/workers/register` with `agent_type` and `worker_url`; retries every 5s on failure; `start_heartbeat_loop(config, worker_id, get_status_fn)` sends heartbeat every `HEARTBEAT_INTERVAL_SECONDS` with current status + task_id (after T017)
- [X] T023 Create stub `worker/src/worker/routes.py` — FastAPI router with `GET /health`; stub `POST /work` returns 202 immediately (no execution yet); `GET /status` returns current in-memory status (`free` initially)
- [X] T024 Implement `worker/src/worker/app.py` — FastAPI app with lifespan: call `register_with_controller()`; start heartbeat loop; include routes (after T022, T023)
- [X] T025 Update `compose.yaml` — add `controller` service (port 8002, `DATABASE_URL`, `API_URL`, depends on migrate+api); update `worker` service env vars: add `CONTROLLER_URL`, `AGENT_TYPE`, `WORK_DIR`; remove `POLL_INTERVAL_SECONDS`, `LEASE_TTL_SECONDS`, `API_URL` (after T021, T024)

**Checkpoint**: Worker registers, appears in `GET /workers`, and tasks are delegated to it (worker accepts with 202 stub).

---

## Phase 4: User Story 2 — Task Execution and Completion Reporting (P1)

**Goal**: After receiving a task, the worker executes the agent (cloning if needed) and reports completion via heartbeat. Controller updates job status in DB.

**Independent Test**: Issue a task to the worker via `POST /work`. Observe agent execution. Verify task status transitions to `completed` or `failed` in the main DB.

### Tests for User Story 2 ⚠️ Write FIRST — confirm RED before implementing

- [X] T026 Write `worker/tests/test_agent_runner.py` — update existing tests: `run_coding_agent()` accepts `WorkRequest` dataclass (no DB session); still calls `clone_repository` when git_url set; still passes github_token to clone; returns `(True, None)` on success; `(False, error)` on agent error; persists `WorkExecution` record to worker DB
- [X] T027 Write `worker/tests/test_routes.py` — tests for `POST /work`: 202 when free; 409 when in_progress; background task starts; `GET /status` reflects in_progress during execution and completed after
- [X] T028 Write `controller/tests/test_delegator_completion.py` — test that heartbeat with `status: "completed"` triggers DB update: job.status → completed, job.completed_at set, worker registry status → completed; heartbeat with `status: "failed"` similarly

### Implementation for User Story 2

- [X] T029 Refactor `worker/src/worker/agent_runner.py` — remove `AsyncSession` parameter; add `WorkRequest` dataclass input (`task_id`, `requirements`, `git_url`, `branch`, `github_token`, `llm_config`, `work_dir`); persist `WorkExecution` record to worker DB at start and update on completion; keep git clone logic and CodingAgent invocation (after T026)
- [X] T030 Update `worker/src/worker/routes.py` — implement `/work` endpoint: validate worker is free (409 if not); set status to in_progress; start `agent_runner.run()` as `asyncio.create_task()`; update status to completed/failed on task completion (after T027, T029)
- [X] T031 Update `worker/src/worker/registration.py` — heartbeat payload includes `status`, `task_id`, `error_message` from current execution state (after T030)
- [X] T032 Update `controller/src/controller/routes.py` — heartbeat handler: when payload `status` is `completed` or `failed`, call `_process_task_completion(worker_record, payload)` which updates `jobs` in main DB (status, completed_at, error_message) and updates registry (after T028)

**Checkpoint**: Full execution flow — task delegated → agent runs → completion reflected in DB.

---

## Phase 5: User Story 3 — Health Monitoring and Lease Renewal (P2)

**Goal**: Controller detects crashed workers and releases their task leases. Controller refreshes leases for actively heartbeating workers.

**Independent Test**: Assign a task to a worker, stop its heartbeat. Verify that after `HEARTBEAT_TIMEOUT_SECONDS` the task reverts to `pending` and can be reassigned.

### Tests for User Story 3 ⚠️ Write FIRST — confirm RED before implementing

- [X] T033 Write `controller/tests/test_heartbeat_timeout.py` — test `_reap_unreachable_workers()`: worker with stale `last_heartbeat_at` is marked unreachable; associated in_progress job is reset to pending (lease_holder=None, lease_expires_at=None, assigned_worker_id=None)
- [X] T034 Write `controller/tests/test_lease_renewal.py` — test `_renew_active_leases()`: in_progress worker with recent heartbeat gets `lease_expires_at` extended; unreachable worker's lease is NOT renewed

### Implementation for User Story 3

- [X] T035 Add `_reap_unreachable_workers()` to `controller/src/controller/delegator.py` — called at start of each poll cycle; finds workers where `last_heartbeat_at < now - HEARTBEAT_TIMEOUT_SECONDS`; marks them "unreachable" in registry; for each, resets their in_progress job to pending (after T033)
- [X] T036 Add `_renew_active_leases()` to `controller/src/controller/delegator.py` — called on each poll cycle; for each "in_progress" worker with recent heartbeat, extends job `lease_expires_at = now + LEASE_TTL_SECONDS` (after T034)

**Checkpoint**: Crashed workers are detected and their tasks become reclaimable.

---

## Phase 6: User Story 4 — Post-Task Cleanup (P2)

**Goal**: User initiates cleanup on a completed/failed task. Controller instructs worker to delete its working directory. Task transitions to `cleaned` and worker becomes `free`.

**Independent Test**: Complete a task. `POST /tasks/{id}/cleanup`. Verify task status → `cleaning_up` → `cleaned` and worker status → `free`.

### Tests for User Story 4 ⚠️ Write FIRST — confirm RED before implementing

- [X] T037 Write tests in `api/tests/unit/test_task_service.py` — `initiate_cleanup()`: task in completed → status set to cleaning_up; task in failed → status set to cleaning_up; task in in_progress → raises 409; task not found → raises 404
- [X] T038 Write `worker/tests/test_routes_free.py` — `POST /free`: worker in completed → deletes work dir → returns freed=true → status resets to free; worker in in_progress → 409; work dir missing → still returns freed=true (idempotent)
- [X] T039 Write `controller/tests/test_cleanup.py` — `_handle_cleaning_up_tasks()`: finds jobs with status cleaning_up; calls worker /free; on success sets job status to cleaned; on worker error leaves job in cleaning_up

### Implementation for User Story 4

- [X] T040 Add `initiate_cleanup()` to `api/src/api/services/task_service.py` — validates task exists and status is completed or failed; sets status to cleaning_up; returns updated task (after T037)
- [X] T041 Add `POST /tasks/{task_id}/cleanup` to `api/src/api/routes/tasks.py` — calls `initiate_cleanup()`; returns `CleanupResponse` (after T040)
- [X] T042 Add `_handle_cleaning_up_tasks()` to `controller/src/controller/delegator.py` — finds cleaning_up jobs with `assigned_worker_url`; POSTs to `{worker_url}/free`; on success: sets job status to cleaned in DB and registry status to free (after T039)
- [X] T043 Implement `POST /free` in `worker/src/worker/routes.py` — rejects if in_progress (409); deletes `{WORK_DIR}/{task_id}/` (idempotent if missing); resets in-memory status to free; clears current_task_id (after T038)
- [X] T044 Add "Clean Up" button to `web/src/app/tasks/[id]/page.tsx` — visible when task status is `completed` or `failed`; calls `POST /tasks/{id}/cleanup` via generated client; shows loading state; refreshes task status after success

**Checkpoint**: Full cleanup flow works end-to-end.

---

## Phase 7: User Story 5 — Workers UI Page (P3)

**Goal**: Dedicated `/workers` page showing all registered workers with status, agent type, and heartbeat info.

**Independent Test**: Register two workers. Navigate to `/workers` in the browser. Both appear with correct agent type, status, and last heartbeat.

### Tests for User Story 5 ⚠️ Write FIRST — confirm RED before implementing

- [X] T045 Write `api/tests/unit/test_workers_route.py` — `GET /workers`: when controller reachable, proxies and returns worker list; when controller unreachable, returns 503

### Implementation for User Story 5

- [X] T046 Create `api/src/api/routes/workers.py` — `GET /workers` endpoint: proxies to `{CONTROLLER_URL}/workers` via httpx; returns list of `WorkerStatus`; returns 503 if controller unreachable; register in `main.py` (after T045)
- [X] T047 [P] Build `web/src/components/workers/WorkersTable.tsx` — table component showing worker_id (truncated), agent_type, status (with color badge), current_task_id (link if set), last_heartbeat_at (relative time)
- [X] T048 Build `web/src/app/workers/page.tsx` — fetches `GET /workers` via generated client; renders `WorkersTable`; auto-refreshes every 15s (after T047)
- [X] T049 [P] Add "Workers" link to navigation in `web/src/components/layout/` (or equivalent nav component)

**Checkpoint**: `/workers` page displays live worker status.

---

## Phase 8: User Story 6 — Git Push via Worker (P3)

**Goal**: After task completion, user can push agent output to remote via the worker's git push endpoint.

**Independent Test**: Complete a task for an existing project. Trigger push. Verify branch appears on GitHub.

### Tests for User Story 6 ⚠️ Write FIRST — confirm RED before implementing

- [X] T050 Write `worker/tests/test_routes_push.py` — `POST /push`: worker in completed with git_url → pushes and returns branch_name/remote_url/pushed_at; worker in in_progress → 409; no git_url configured → 422; git push fails → 502
- [X] T051 Write updated `api/tests/unit/test_task_service.py` — `trigger_push()`: reads `assigned_worker_url` from job; proxies POST to worker `/push`; returns PushResponse; if `assigned_worker_url` null → 422

### Implementation for User Story 6

- [X] T052 Implement `POST /push` in `worker/src/worker/routes.py` — rejects if not in completed state (409); calls `git_utils.push_working_directory_to_remote()` using stored `git_url` and `github_token` from the WorkRequest received during task assignment; returns `PushResponse` (after T050)
- [X] T053 Update `api/src/api/services/task_service.py` `trigger_push()` — instead of calling `git_service` directly, reads `job.assigned_worker_url`; proxies `POST {assigned_worker_url}/push` via httpx; maps worker response to `PushResponse`; falls back to existing git_service logic if `assigned_worker_url` is null (for backwards compatibility) (after T051)

**Checkpoint**: End-to-end push flow works via worker.

---

## Phase 9: Polish & Cleanup

**Purpose**: Remove legacy code, lint, and final validation.

- [X] T054 Remove `api/src/api/services/setting_service.py` `agent.work.path` entry from `ALLOWED_KEYS` and `DEFAULTS`
- [X] T055 [P] Update `api/tests/unit/test_setting_service.py` — remove `agent.work.path` from expected defaults; update key count assertion
- [X] T056 [P] Delete `worker/src/worker/lease_manager.py` (fully superseded by Controller)
- [X] T057 [P] Remove old polling-loop code from worker — if `worker/src/worker/worker.py` still exists, delete it (replaced by `app.py`); ensure nothing imports from it
- [X] T058 [P] Run `ruff check src/` in `controller/`, `worker/`, `api/` — fix all lint errors
- [X] T059 [P] Run `cd web && npx tsc --noEmit` — fix all TypeScript type errors
- [X] T060 Update `MEMORY.md` — record new Controller service, worker DB schema, updated worker directory layout

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** (Setup): No dependencies — start immediately
- **Phase 2** (Foundational): Depends on Phase 1 (T001 required for T006) — BLOCKS all story phases
- **Phase 3** (US1 P1): Depends on Phase 2 completion
- **Phase 4** (US2 P1): Depends on Phase 3 (controller delegation must work before completion reporting)
- **Phase 5** (US3 P2): Depends on Phase 4 (completion flow must exist before testing recovery)
- **Phase 6** (US4 P2): Depends on Phase 4 (tasks must reach completed/failed before cleanup)
- **Phase 7** (US5 P3): Depends on Phase 3 (workers endpoint requires registration to be working)
- **Phase 8** (US6 P3): Depends on Phase 4 (task must be completed to push)
- **Phase 9** (Polish): Depends on all prior phases

### User Story Dependencies

- **US1 → US2**: US2 extends the /work endpoint stub from US1; US1 MUST complete first
- **US2 → US3**: Lease renewal only meaningful after full execution flow (US2) is in place
- **US2 → US4**: Cleanup only relevant after task can reach completed/failed (US2)
- **US1 → US5**: Workers page requires registration (US1) to show data
- **US2 → US6**: Push only valid after task reaches completed (US2)

### Within Each User Story

1. Tests MUST be written and confirmed **RED** before implementation begins
2. Models before services before endpoints
3. Controller changes before Worker changes (worker adapts to controller protocol)

### Parallel Opportunities

Within Phase 2: T007, T008, T009, T010, T011, T012, T013 can all run in parallel
Within Phase 3 tests: T014, T015, T016, T017 can run in parallel (write simultaneously)
Within Phase 9: T055, T056, T057, T058, T059, T060 can all run in parallel

---

## Notes

- `[P]` = task operates on different files than sibling tasks; can run in parallel
- `[USN]` label maps task to user story for traceability
- All Python files: type hints required, `ruff` must pass, `@pytest.mark.asyncio` on async tests if running from repo root
- Sensitive values (github_token, API keys): never logged — use `***` or sanitized URLs in logs
- Commit after each user story phase completes (or more frequently for reviewability)
