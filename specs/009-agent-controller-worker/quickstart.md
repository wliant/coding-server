# Quickstart: Agent Controller / Worker Redesign

**Branch**: `009-agent-controller-worker` | **Date**: 2026-03-08

---

## New Services

This feature introduces a **Controller** service and refactors the **Worker** service.

### Directory Layout (Post-Implementation)

```
coding-server/
├── controller/              ← NEW service
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic/            ← No DB migrations (in-memory only)
│   ├── src/controller/
│   │   ├── config.py       ← Settings (DATABASE_URL, CONTROLLER_PORT, polling config)
│   │   ├── registry.py     ← In-memory WorkerRegistry (asyncio.Lock-protected dict)
│   │   ├── models.py       ← SQLAlchemy models (Job, Project, Agent — read-only views)
│   │   ├── delegator.py    ← Polling loop: reap → renew → cleanup → delegate
│   │   ├── routes.py       ← FastAPI routes (register, heartbeat, health, workers)
│   │   └── app.py          ← FastAPI app + lifespan (start delegator loop)
│   └── tests/
│
├── worker/                  ← REFACTORED (major changes)
│   ├── pyproject.toml       ← Unchanged dependencies; add alembic
│   ├── Dockerfile           ← Updated CMD; still needs git binary
│   ├── alembic/             ← NEW: worker's own migrations (worker_executions table)
│   ├── src/worker/
│   │   ├── config.py        ← Add: CONTROLLER_URL, AGENT_TYPE, WORK_DIR, HEARTBEAT_INTERVAL
│   │   ├── models.py        ← Updated: WorkExecution model (worker_executions table)
│   │   ├── git_utils.py     ← Unchanged
│   │   ├── agent_runner.py  ← Refactored: no DB session; accepts WorkRequest dataclass
│   │   ├── registration.py  ← NEW: register_with_controller() + heartbeat loop
│   │   ├── routes.py        ← NEW: FastAPI routes (/work, /status, /push, /free, /health)
│   │   └── app.py           ← Refactored: start registration + heartbeat on lifespan
│   │   # REMOVED: lease_manager.py, worker.py (old polling loop)
│   └── tests/
│
└── compose.yaml             ← Add controller service; update worker env vars
```

---

## Environment Variables

### Controller

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | (required) | Same PostgreSQL URL as main API |
| `API_URL` | `http://api:8000` | Main API URL for fetching agent settings |
| `CONTROLLER_PORT` | `8002` | Port to listen on |
| `POLL_INTERVAL_SECONDS` | `10` | How often the Controller polls for work |
| `HEARTBEAT_TIMEOUT_SECONDS` | `60` | Time without heartbeat before worker is "unreachable" |
| `LEASE_TTL_SECONDS` | `300` | Initial lease duration for claimed tasks |

### Worker

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | (required) | Same PostgreSQL (for worker's own schema) |
| `CONTROLLER_URL` | `http://controller:8002` | Controller base URL |
| `AGENT_TYPE` | (required) | Agent type this worker handles |
| `WORK_DIR` | `/agent-work` | Base directory for working directories |
| `WORKER_PORT` | `8001` | Port to listen on |
| `HEARTBEAT_INTERVAL_SECONDS` | `15` | Frequency of heartbeat calls to Controller |
| `TOOLS_GATEWAY_URL` | `http://tools:8002` | FastMCP tool server URL |

---

## Running Locally (Dev)

```bash
# Start all services (includes new controller)
task dev

# View controller logs
docker compose -f compose.yaml -f compose.dev.yaml logs -f controller

# View worker logs
docker compose -f compose.yaml -f compose.dev.yaml logs -f worker

# Run controller tests
docker compose -f compose.yaml -f compose.dev.yaml exec controller pytest tests/ -v

# Run worker tests
docker compose -f compose.yaml -f compose.dev.yaml exec worker pytest tests/ -v

# Run API tests
docker compose -f compose.yaml -f compose.dev.yaml exec api pytest tests/ -v
```

---

## Key Flows

### Worker Startup
1. Worker starts → reads `CONTROLLER_URL`, `AGENT_TYPE`, `WORK_DIR` from env
2. Worker calls `POST {CONTROLLER_URL}/workers/register` with agent_type + worker_url
3. If Controller unreachable, retries every 5s until success
4. On success, stores `worker_id` in memory
5. Starts heartbeat loop (every `HEARTBEAT_INTERVAL_SECONDS`)

### Task Execution
1. Controller poll cycle finds pending task matching free worker
2. Controller atomically claims task in DB; calls `POST {worker_url}/work`
3. Worker accepts (202), starts agent in background
4. Worker heartbeats every 15s with `status: "in_progress", task_id: ...`
5. On completion, worker sends heartbeat with `status: "completed"` or `"failed"`
6. Controller updates job in DB; worker status becomes "completed"/"failed"

### Cleanup
1. User clicks "Clean Up" on a completed/failed task
2. `POST /tasks/{id}/cleanup` (main API) → sets job status to "cleaning_up"
3. Controller poll cycle detects cleaning_up task with `assigned_worker_id`
4. Controller calls `POST {worker_url}/free`
5. Worker deletes `{WORK_DIR}/{task_id}/`, reports success
6. Controller sets job status to "cleaned", worker status to "free"

### Push
1. User clicks "Push to Remote" on a completed task
2. `POST /tasks/{id}/push` (main API) → reads `assigned_worker_url` from job record
3. Main API proxies to `POST {assigned_worker_url}/push`
4. Worker runs git push from its working directory using stored github_token
5. Returns branch_name, remote_url, pushed_at

---

## Verifying the Setup

```bash
# Check controller registered workers
curl http://localhost:8002/workers | jq .

# Check worker status
curl http://localhost:8001/status | jq .

# Check controller health
curl http://localhost:8002/health

# Check via main API (after codegen)
curl http://localhost:8000/workers | jq .
```
