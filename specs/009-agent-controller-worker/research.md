# Research: Agent Controller / Worker Redesign

**Branch**: `009-agent-controller-worker` | **Date**: 2026-03-08

---

## Decision 1 — Controller Service Location

**Decision**: New top-level `controller/` package alongside existing `worker/`, `api/`, `web/`.

**Rationale**: The Controller is a wholly new service with distinct responsibilities (coordination, registry, lease management, delegation). Co-locating with the worker would violate SRP. Mirroring the existing package layout (separate `pyproject.toml`, `src/`, `tests/`, `Dockerfile`) gives it the same dev/test/build experience as other services.

**Alternatives Considered**:
- Embedding controller logic in the API: rejected — API is user-facing; controller is internal coordination; merging them couples two different concerns and complicates independent deployment.
- Embedding controller logic in the existing worker: rejected — the worker is being redesigned to be execution-only; adding coordination would recreate the current monolithic problem.

---

## Decision 2 — Controller Worker Registry

**Decision**: In-memory Python dict keyed by `worker_id` (clarified by user: Option A).

**Rationale**: Simplest possible implementation; avoids DB schema for ephemeral worker state. Workers are responsible for re-registering after a Controller restart (retry loop on startup). Heartbeat timeout handles stale registrations.

**Data structure**:
```python
@dataclass
class WorkerRecord:
    worker_id: str           # UUID str assigned by Controller
    agent_type: str          # e.g. "simple_crewai_pair_agent"
    worker_url: str          # http://worker-host:8001
    status: Literal["free", "in_progress", "completed", "failed", "unreachable"]
    last_heartbeat_at: datetime
    current_task_id: str | None
    registered_at: datetime
```

Registry: `dict[str, WorkerRecord]` protected by `asyncio.Lock`.

**Alternatives Considered**:
- Redis: rejected (adds dependency; overkill for single-controller deployment).
- Postgres table: rejected (user's explicit choice; adds migration; ephemeral data).

---

## Decision 3 — Controller Database Access

**Decision**: Direct DB connection using SQLAlchemy async (same PostgreSQL instance as main API). Controller reads `jobs`, `projects`, `agents` tables; writes `jobs` (status, lease, assigned_worker_id, assigned_worker_url) (clarified by user: Option A).

**Rationale**: Low-latency polling requires tight DB coupling. Atomic lease-claim via `UPDATE … WHERE status='pending'` is simpler over direct SQL than over HTTP. Controller shares the same `DATABASE_URL` env var.

**Controller DB access pattern**:
- Reads: `SELECT jobs WHERE status='pending'` (with agent join for agent_type matching)
- Writes: `UPDATE jobs SET status, lease_holder, lease_expires_at, assigned_worker_id, assigned_worker_url`
- No writes to `projects`, `agents`, `work_directories`

**Alternatives Considered**:
- Via main API HTTP: rejected (added latency; HTTP atomicity for lease operations requires dedicated endpoints; constitutes tight API coupling).

---

## Decision 4 — Task Delegation Flow

**Decision**: Controller polling loop performs the following on each cycle (default: every 10s):

1. **Reap**: Find workers with `last_heartbeat_at < now - HEARTBEAT_TIMEOUT`; mark them "unreachable". For each such worker's `current_task_id`, reset job status to "pending", clear lease fields.
2. **Lease renewal**: For each "in_progress" worker still alive, extend `lease_expires_at = now + LEASE_TTL`.
3. **Handle cleanup**: Find jobs with `status = 'cleaning_up'`; call associated worker's `/free` endpoint.
4. **Delegation**: For each pending job (ordered by `created_at ASC`): find a free worker whose `agent_type` matches the job's agent. If found: atomically claim job (`UPDATE WHERE status='pending'`); if claim succeeds, `POST worker_url/work`. If worker call fails, rollback claim to "pending".
5. **Process completions**: Workers report completion via heartbeat payload (see Decision 6). Controller updates job status accordingly.

---

## Decision 5 — Task Data Passed to Worker

**Decision**: Controller passes all needed config in the `/work` request body, so the Worker has zero external dependencies except its working directory and the Controller URL.

Worker `/work` payload includes:
- `task_id`, `requirements`, `git_url | null`, `branch | null`
- `github_token | null` (fetched from main API settings by Controller before delegation)
- `llm_config` dict (fetched from main API settings by Controller before delegation)
- `work_dir` (absolute path the worker should use; Controller computes from worker's own configured base dir... actually the worker configures its own `WORK_DIR`)

**Refinement**: The worker's working directory base path (`AGENT_WORK_DIR`) is configured on the worker via env var. The Controller passes `task_id` and the worker constructs `{AGENT_WORK_DIR}/{task_id}/`. This avoids the Controller needing to know the worker's filesystem layout.

The Controller fetches `github_token` and LLM config from the main API `GET /settings` before issuing work to the worker. These are included in the `/work` payload.

---

## Decision 6 — Worker Completion Reporting

**Decision**: Workers report status (including completion) via the heartbeat payload. Heartbeat body includes `{ status, task_id }`. When the Controller receives a heartbeat with `status: "completed"` or `status: "failed"`, it:
1. Updates `jobs SET status=<status>, completed_at=now, error_message=<msg>` in DB.
2. Updates worker registry entry to "completed" or "failed".

This keeps the Controller API to exactly the 4 endpoints specified, with heartbeat serving dual purpose.

**Alternatives Considered**:
- Dedicated callback endpoint on Controller: rejected — adds a 5th Controller endpoint beyond spec; adds complexity.
- Controller polls worker `/status` on every cycle: rejected — introduces N HTTP calls per poll cycle (one per active worker); heartbeat is more efficient.

---

## Decision 7 — Push Flow

**Decision**: Keep the existing main API `POST /tasks/{id}/push` endpoint. In the new design it reads `assigned_worker_url` from the job record (stored by Controller at delegation time) and proxies the push request to `{assigned_worker_url}/push`. The Worker's `/push` endpoint uses its local working directory to run the git push.

This preserves the existing UI/client without changes to the push button behaviour.

**Alternatives Considered**:
- Main API calls git_service directly (as before): rejected — Worker's working dir may not be on the shared volume in all deployments.
- Controller proxies push: rejected — Controller is coordination-only; push is task-data operation.

**Note**: For the initial Docker Compose deployment, the shared `agent_work` volume is retained between API and worker. The `assigned_worker_url` approach generalises to distributed deployments.

---

## Decision 8 — Worker Own Database Schema

**Decision**: Worker uses the same PostgreSQL instance as the main API, but with table name prefix `worker_`. Tables:
- `worker_executions`: persists task execution state (task_id, status, started_at, completed_at, error_message, agent_type)

Worker manages its own Alembic migrations in `worker/alembic/` (separate from `api/alembic/`).

**Rationale**: Separate schema/prefix prevents accidental coupling to main API schema. Shared DB server avoids adding another DB dependency in the Docker Compose setup.

**Alternatives Considered**:
- SQLite: rejected — async SQLite has limitations; would diverge from rest of project.
- Separate Postgres database: rejected — adds Docker Compose complexity (new service, new volume).
- Shared tables with main API: rejected — couples worker lifecycle to main API schema ownership.

---

## Decision 9 — Inter-Service Authentication

**Decision**: No authentication between Controller and Worker APIs (clarified by user: Option A). Network isolation (Docker internal network `backend`) is the sole protection.

---

## Decision 10 — Migration Strategy

**Decision**: Full replacement of existing worker service (clarified by user: Option A). The current `worker/` package is refactored in-place:
- Remove: `lease_manager.py`, `main_loop()` polling in `worker.py`
- Keep/adapt: `git_utils.py`, `agent_runner.py` (remove DB session param), `config.py` (add new env vars)
- Add: registration client, heartbeat loop, REST API endpoints for `/work`, `/status`, `/push`, `/free`

New `controller/` package is created fresh.

Existing `compose.yaml` worker service is updated; controller service is added.

---

## Decision 11 — Workers UI Placement

**Decision**: Dedicated `/workers` page in the Next.js app with its own navigation link (clarified by user: Option B).

---

## Decision 12 — API-First Compliance (Constitution Principle VI)

Three OpenAPI specs must be authored before implementation:
1. **Main `openapi.json`**: Add `cleaning_up`, `cleaned` to TaskStatus enum; add `POST /tasks/{id}/cleanup`; add `GET /workers` (proxy to Controller); add `assigned_worker_id` to TaskDetailResponse; bump version.
2. **`controller/openapi.json`**: Define 4 Controller endpoints.
3. **`worker/openapi.json`**: Define 5 Worker endpoints (health, work, status, push, free).

TypeScript client (`web/src/client/`) is regenerated from main `openapi.json` only (Controller and Worker APIs are internal, not called from browser).

---

## Resolved NEEDS CLARIFICATION

None — all questions resolved via spec clarification session (2026-03-08).
