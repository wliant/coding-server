# Implementation Plan: Agent Controller / Worker Redesign

**Branch**: `009-agent-controller-worker` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)

## Summary

Replace the current monolithic timer-based worker (polling + executing in one process) with a **Controller** service (coordination, lease management, delegation) and one or more **Worker** services (registration, execution, status reporting). The Controller holds an in-memory worker registry, polls the main PostgreSQL database directly for pending tasks, matches them to free workers by agent type, and delegates work via HTTP. Workers register on startup, send heartbeats (which also carry completion status), and expose REST endpoints for receiving tasks, git push, and cleanup. Two new task statuses (`cleaning_up`, `cleaned`) model the post-execution cleanup flow. A new `/workers` page in the UI shows operational worker status.

---

## Technical Context

**Language/Version**: Python 3.12 (controller, worker); TypeScript / Node.js 20 (web)
**Primary Dependencies**: FastAPI 0.115+, SQLAlchemy 2 async, asyncpg, pydantic-settings, python-json-logger, httpx (controller and worker); simple-crewai-pair-agent, gitpython (worker); Next.js 15, React 19, Tailwind CSS, shadcn/ui, @hey-api/client-fetch (web)
**Storage**: PostgreSQL 16 — shared instance; Controller accesses main `jobs`/`projects`/`agents` tables directly; Worker has its own `worker_executions` table (same DB, `worker_` prefix)
**Testing**: pytest + pytest-asyncio (Python); playwright (e2e)
**Target Platform**: Linux containers (Docker Compose)
**Project Type**: Multi-service web application
**Performance Goals**: Worker registration < 5s; task delegation within 2 poll cycles (≤ 20s); cleanup < 30s
**Constraints**: Default heartbeat timeout 60s; poll interval 10s; lease TTL 300s; no inter-service auth (network isolation only)
**Scale/Scope**: Single Controller, 1–N workers per deployment; N bounded by available agent-work volume space

---

## Constitution Check

### Principle I — Simplicity-First ✅
In-memory registry (no extra DB schema for Controller). Direct DB access (no HTTP indirection for Controller→DB). Heartbeat serves dual purpose (liveness + completion report) avoiding a 5th Controller endpoint. Worker's own DB uses table prefix (no separate Postgres schema). See Complexity Tracking for justified additions.

### Principle II — TDD (NON-NEGOTIABLE) ✅
All implementation tasks require tests written before code. Tests confirm Red state before implementation begins. Each user story has independently runnable tests. Acceptance scenarios from spec.md map directly to test cases.

### Principle III — Modularity & SRP ✅
Controller: coordination only (no execution logic).
Worker: execution only (no DB polling, no lease management).
Git utilities: isolated in `git_utils.py`.
In-memory registry: isolated in `registry.py`.
Contracts defined in `specs/009-agent-controller-worker/contracts/`.

### Principle IV — Observability ✅
All key events MUST emit structured JSON logs:
- Controller: `worker_registered`, `task_delegated`, `delegation_failed`, `worker_unreachable`, `lease_renewed`, `cleanup_initiated`, `task_completed`, `task_failed`
- Worker: `registration_success`, `registration_retry`, `work_received`, `clone_started`, `clone_succeeded`, `clone_failed`, `agent_starting`, `agent_completed`, `agent_failed`, `push_succeeded`, `push_failed`, `cleanup_started`, `cleanup_succeeded`, `cleanup_failed`, `heartbeat_sent`
- Sensitive data (github_token, API keys) MUST NOT appear in any log entry.

### Principle V — Incremental Delivery ✅
6 user stories, each independently testable and deliverable:
- P1a: Worker registers and Controller delegates (no execution yet — stub worker endpoint)
- P1b: Task execution and completion reporting (agent runner integration)
- P2a: Health monitoring and lease renewal
- P2b: Post-task cleanup flow
- P3a: Workers UI page
- P3b: Git push via worker

### Principle VI — API-First with OpenAPI (NON-NEGOTIABLE) ✅
**Three** OpenAPI specs authored before any implementation:
1. Root `openapi.json` updated (new statuses, cleanup + workers endpoints, TaskDetailResponse addition)
2. `controller/openapi.json` authored (4 endpoints)
3. `worker/openapi.json` authored (5 endpoints)
TypeScript client regenerated from root `openapi.json` only.

**GATE: All three specs must be committed and reviewed before any Python/TypeScript implementation begins.**

---

## Complexity Tracking

| Addition | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| New `controller/` service (4th Python package) | Spec explicitly requires Controller as a separate service; coordination state (in-memory registry) must not be in a stateless service | Embedding in API violates SRP; embedding in worker recreates the monolithic problem being solved |
| Worker's own `worker_executions` DB table | Spec requires workers to persist execution state independently of main API DB ownership | Writing to main `jobs` table from worker couples worker to main API schema; SQLite rejected (async limitations, diverges from project stack) |
| Heartbeat dual-purpose (liveness + status report) | Keeps Controller API at exactly 4 endpoints per spec; avoids a dedicated callback endpoint | Controller polling worker `/status` every cycle = N HTTP calls per poll; dedicated 5th endpoint exceeds spec scope |
| `assigned_worker_url` field in `jobs` table | Main API needs to proxy push to worker; Controller registry is in-memory only (can't be queried by API) | Exposing worker URL via Controller endpoint creates tight API→Controller coupling for every push request |

---

## Project Structure

### Documentation (this feature)

```text
specs/009-agent-controller-worker/
├── plan.md              ← This file
├── spec.md              ← Feature specification
├── research.md          ← Phase 0 research decisions
├── data-model.md        ← Entity definitions and state transitions
├── quickstart.md        ← Dev setup guide
├── contracts/
│   ├── controller-api.yaml    ← Controller OpenAPI spec
│   ├── worker-api.yaml        ← Worker OpenAPI spec
│   └── main-api-changes.md   ← Changes to root openapi.json
├── checklists/
│   └── requirements.md
└── tasks.md             ← Phase 2 output (/speckit.tasks command)
```

### Source Code Changes

```text
controller/                     ← NEW Python package
├── Dockerfile
├── pyproject.toml
├── src/controller/
│   ├── __init__.py
│   ├── app.py              ← FastAPI app + lifespan (starts delegator)
│   ├── config.py           ← pydantic-settings (DATABASE_URL, API_URL, POLL_INTERVAL, etc.)
│   ├── registry.py         ← WorkerRecord dataclass + WorkerRegistry (asyncio.Lock + dict)
│   ├── models.py           ← SQLAlchemy ORM for main DB tables (Job, Project, Agent) — read/write
│   ├── delegator.py        ← Polling loop: reap → renew leases → handle cleaning_up → delegate
│   └── routes.py           ← /workers/register, /workers/{id}/heartbeat, /health, /workers
└── tests/
    ├── conftest.py
    ├── test_registry.py
    ├── test_delegator.py
    └── test_routes.py

worker/                         ← REFACTORED (major changes)
├── Dockerfile                  ← Updated CMD
├── pyproject.toml              ← Add alembic dependency
├── alembic/                    ← NEW: worker's own migrations
│   ├── env.py
│   └── versions/
│       └── worker_0001_create_worker_executions.py
├── src/worker/
│   ├── app.py                  ← NEW: FastAPI app + lifespan (registration + heartbeat)
│   ├── config.py               ← Add CONTROLLER_URL, AGENT_TYPE, WORK_DIR, HEARTBEAT_INTERVAL
│   ├── models.py               ← Replace Job/Project with WorkExecution (worker_executions table)
│   ├── git_utils.py            ← Unchanged
│   ├── agent_runner.py         ← Refactored: remove DB session param; accept WorkRequest
│   ├── registration.py         ← NEW: register_with_controller() + start_heartbeat_loop()
│   └── routes.py               ← NEW: /work, /status, /push, /free, /health
│   # DELETED: lease_manager.py, worker.py (old monolithic polling loop)
└── tests/
    ├── conftest.py             ← Updated fixtures
    ├── test_registration.py    ← NEW
    ├── test_routes.py          ← NEW
    ├── test_agent_runner.py    ← Updated (remove DB session from run_coding_agent)
    └── test_git_utils.py       ← Unchanged

api/
├── alembic/versions/
│   └── 0009_add_worker_fields_to_jobs.py   ← NEW migration
├── src/api/
│   ├── models/job.py           ← Add assigned_worker_id, assigned_worker_url columns
│   ├── schemas/task.py         ← Add cleaning_up/cleaned to TaskStatus; add CleanupResponse, WorkerStatus; update TaskDetailResponse
│   ├── routes/tasks.py         ← Add POST /tasks/{id}/cleanup
│   ├── routes/workers.py       ← NEW: GET /workers (proxies to Controller)
│   ├── services/task_service.py ← Add initiate_cleanup(); update trigger_push() to proxy to worker
│   └── services/setting_service.py ← Remove agent.work.path from ALLOWED_KEYS and DEFAULTS
└── tests/
    ├── unit/test_task_service.py   ← Add cleanup tests
    └── unit/test_setting_service.py ← Update: remove agent.work.path from expected keys

web/
├── src/
│   ├── client/             ← Regenerated from root openapi.json
│   ├── app/
│   │   ├── workers/
│   │   │   └── page.tsx    ← NEW: Workers status page
│   │   └── tasks/
│   │       └── [id]/
│   │           └── page.tsx ← Updated: add "Clean Up" button for completed/failed tasks
│   └── components/
│       ├── workers/
│       │   └── WorkersTable.tsx  ← NEW
│       └── tasks/
│           └── CleanupButton.tsx ← NEW

openapi.json                ← Updated (version bump, new endpoints, new statuses)
compose.yaml                ← Add controller service; update worker env vars
```

---

## Implementation Order (Story-by-Story)

### Story 1 — Worker Registration and Task Delegation (P1)

1. Update `openapi.json` (all three specs) — API-First gate
2. Regenerate TypeScript client
3. Migration 0009 (add `assigned_worker_id`, `assigned_worker_url` to jobs)
4. Write `controller/` package: config, registry, models, routes (register + heartbeat + health + list)
5. Write `delegator.py`: polling loop with delegation logic (stub — calls /work but worker is stub)
6. Write controller tests (TDD)
7. Refactor `worker/config.py`: add CONTROLLER_URL, AGENT_TYPE, WORK_DIR, HEARTBEAT_INTERVAL
8. Write `worker/registration.py`: register_with_controller() + heartbeat loop
9. Write `worker/routes.py`: stub /work endpoint (202 immediate), /status, /health
10. Write worker registration tests (TDD)
11. Update `compose.yaml`: add controller service, update worker env vars

### Story 2 — Task Execution and Completion Reporting (P1)

1. Write worker `WorkExecution` DB model + alembic migration
2. Refactor `agent_runner.py`: remove DB session; accept WorkRequest dataclass; store execution state in worker DB
3. Update `/work` endpoint to start agent_runner in background task
4. Update heartbeat to carry status/error from completed execution
5. Update controller delegator to process completion heartbeats (update job in main DB)
6. Write tests (TDD): agent_runner unit tests, integration tests for full delegation→execution→completion flow

### Story 3 — Health Monitoring and Lease Renewal (P2)

1. Add heartbeat timeout reaping logic to delegator
2. Add lease renewal logic to delegator (extend lease_expires_at for alive workers)
3. Write tests (TDD): simulate heartbeat timeout, verify task returns to pending

### Story 4 — Post-Task Cleanup (P2)

1. Add `initiate_cleanup()` to `task_service.py`
2. Add `POST /tasks/{id}/cleanup` route to API
3. Add cleanup detection to controller delegator (call worker /free for cleaning_up tasks)
4. Implement `/free` endpoint on worker (delete work dir, reset status)
5. Add "Clean Up" button to task detail page
6. Write tests (TDD): cleanup flow end-to-end

### Story 5 — Workers UI Page (P3)

1. Add `GET /workers` route to main API (proxies to Controller)
2. Build `WorkersTable.tsx` component
3. Build `/workers` page
4. Add navigation link
5. Regenerate client if schema already updated (it should be from Story 1)

### Story 6 — Git Push via Worker (P3)

1. Update `trigger_push()` in task_service to proxy to worker `/push`
2. Implement `/push` endpoint on worker
3. Write tests (TDD)
4. Verify end-to-end: complete task → push → branch appears on GitHub

---

## Key Constraints Reminder

- Token (github_token, API keys) MUST NOT appear in any log line — use sanitized URLs in logs.
- Worker MUST NOT accept a second task while in_progress (409 response).
- Controller MUST rollback DB claim if worker /work call fails (task stays pending).
- Worker /free is idempotent: non-existent working directory → success.
- All new Python functions: type hints required; ruff lint must pass.
- All new API changes: openapi.json updated atomically with code changes.
