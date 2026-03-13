# Orchestration
Last updated: 2026-03-13

## Overview

The controller service is the central coordinator that bridges pending tasks in the database with available workers and sandboxes. It polls for pending tasks, matches them to free workers by agent type, delegates work, monitors health via heartbeats, renews leases, and orchestrates cleanup. It also tracks sandbox registrations for liveness monitoring.

## Domain Concepts

### Worker Lifecycle (from controller's perspective)

| Status | Meaning |
|--------|---------|
| `free` | Registered, no active task, eligible for delegation |
| `in_progress` | Executing a task |
| `completed` | Task finished successfully, awaiting cleanup |
| `failed` | Task finished with error, awaiting cleanup |
| `unreachable` | Heartbeat timeout exceeded |

### Sandbox Lifecycle

| Status | Meaning |
|--------|---------|
| `free` | Registered, available for use |
| `allocated` | Reserved for future use (not currently implemented) |
| `unavailable` | Temporarily unavailable |
| `unreachable` | Heartbeat timeout exceeded |

### Delegation Loop

The controller runs a continuous poll loop (default: every 10 seconds) with four phases executed in order:

1. **Reap unreachable workers/sandboxes** — Mark any worker/sandbox whose last heartbeat exceeds the timeout as `unreachable`; release task leases for unreachable workers so tasks revert to `pending`
2. **Renew active leases** — Refresh lease expiry for tasks whose assigned workers are still healthy (sending heartbeats)
3. **Handle cleaning_up tasks** — For tasks in `cleaning_up` status, call the assigned worker's `/free` endpoint to delete the working directory and free the worker
4. **Delegate pending tasks** — For each pending task, find a free worker matching the task's agent type, atomically claim the task (CAS on status + lease fields), then POST the work payload to the worker's `/work` endpoint

### Lease Pattern

- Controller uses atomic compare-and-set (CAS) updates on the jobs table: `UPDATE jobs SET status='in_progress', lease_holder=:worker_id, lease_expires_at=:ttl WHERE id=:job_id AND status='pending'`
- Lease TTL is configurable (default: 120 seconds)
- Leases are renewed on each poll cycle while the worker is healthy
- Expired leases cause the task to revert to `pending` for re-delegation

### Heartbeat Protocol

- Workers send `POST /workers/{worker_id}/heartbeat` every 15 seconds (configurable)
- Heartbeat body includes current status: `{"status": "in_progress"}` or `{"status": "completed"}` etc.
- If controller returns 404 (after restart, registry lost), worker automatically re-registers
- Sandboxes follow the same pattern: `POST /sandboxes/{sandbox_id}/heartbeat`

## Data Model

The controller connects directly to the main PostgreSQL database and reads/writes the `jobs`, `projects`, `agents`, and `sandboxes` tables. It does NOT have its own separate database.

### In-Memory Registries

#### WorkerRegistry

```python
@dataclass
class WorkerRecord:
    worker_id: str
    agent_type: str
    worker_url: str
    status: str  # free, in_progress, completed, failed, unreachable
    current_task_id: str | None
    last_heartbeat_at: datetime
    registered_at: datetime
```

- Protected by `asyncio.Lock`
- Dict keyed by `worker_id`
- Lost on controller restart; workers re-register automatically

#### SandboxRegistry

```python
@dataclass
class SandboxRecord:
    sandbox_id: str
    sandbox_url: str
    labels: list[str]
    status: str  # free, allocated, unavailable, unreachable
    last_heartbeat_at: datetime
    registered_at: datetime
```

- Same pattern as WorkerRegistry (asyncio.Lock, dict, in-memory only)
- Sandbox registrations are also persisted to the `sandboxes` DB table for UI display

## API Contracts

### Controller Endpoints (port 8003)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/workers/register` | Register a worker; returns `{worker_id}` |
| POST | `/workers/{worker_id}/heartbeat` | Worker heartbeat; returns 404 if unknown |
| GET | `/workers` | List all registered workers with status |
| POST | `/sandboxes/register` | Register a sandbox; returns `{sandbox_id}` |
| POST | `/sandboxes/{sandbox_id}/heartbeat` | Sandbox heartbeat; returns 404 if unknown |
| GET | `/sandboxes` | List all registered sandboxes with status |

### POST /workers/register

```json
// Request
{"agent_type": "simple_crewai_pair_agent", "worker_url": "http://simple_crewai_pair_agent:8001"}

// Response
{"worker_id": "uuid-string"}
```

### POST /sandboxes/register

```json
// Request
{"sandbox_id": "sandbox-uuid", "sandbox_url": "http://sandbox:8006", "labels": ["python", "git"]}

// Response
{"sandbox_id": "sandbox-uuid"}
```

### GET /workers Response

```json
[
  {
    "worker_id": "uuid",
    "agent_type": "simple_crewai_pair_agent",
    "status": "free",
    "current_task_id": null,
    "worker_url": "http://simple_crewai_pair_agent:8001",
    "last_heartbeat_at": "2026-03-13T10:00:00Z",
    "registered_at": "2026-03-13T09:00:00Z"
  }
]
```

### API Proxy Routes (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/workers` | Proxies to controller `GET /workers` |
| GET | `/sandboxes` | Proxies to controller `GET /sandboxes` |

The main API proxies these requests to the controller using `httpx`.

## Service Architecture

```
agents-controller/src/controller/
├── app.py          # FastAPI app with lifespan (delegator loop startup)
├── config.py       # Settings: DATABASE_URL, API_URL, CONTROLLER_PORT, timeouts
├── delegator.py    # Poll loop: reap → renew → cleanup → delegate
├── models.py       # SQLAlchemy ORM models (Job, Project, Agent, Sandbox)
├── registry.py     # WorkerRegistry + SandboxRegistry (or sandbox_registry.py)
├── routes.py       # HTTP endpoints for register/heartbeat/list
```

### Configuration (environment variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `API_URL` | `http://api:8000` | Main API URL |
| `CONTROLLER_PORT` | `8003` | Controller listen port |
| `POLL_INTERVAL_SECONDS` | `10` | Delegation loop interval |
| `HEARTBEAT_TIMEOUT_SECONDS` | `60` | Worker heartbeat timeout before marking unreachable |
| `LEASE_TTL_SECONDS` | `300` | Task lease duration (5 minutes) |
| `SANDBOX_HEARTBEAT_TIMEOUT_SECONDS` | `60` | Sandbox heartbeat timeout |

## UI Components

### WorkersTable (`web/src/components/workers/WorkersTable.tsx`)

- Columns: Worker ID, Agent Type, Status (badge), Current Task, Worker URL, Last Heartbeat (relative time)
- Accessible at `/workers` page
- Auto-refreshes every 15 seconds

### SandboxesTable (`web/src/components/sandboxes/SandboxesTable.tsx`)

- Columns: Sandbox ID, Status (badge), Labels (pill badges), URL, Last Heartbeat (relative time)
- Accessible at `/sandboxes` page
- Auto-refreshes every 15 seconds
- Empty state: "No sandboxes registered. Start a sandbox service to see it here."

### Navigation

Both Workers and Sandboxes pages are accessible from the sidebar navigation.

## Configuration

See environment variables table above. All timeouts are configurable via environment variables with sensible defaults.

## Cross-Context Dependencies

- **Task Lifecycle**: Controller reads `jobs` table for pending tasks, updates status/lease fields
- **Agent Execution**: Controller delegates to workers via HTTP, monitors heartbeats
- **Platform Infrastructure**: Controller reads `agents` table to match task agent_id to worker agent_type; writes `sandboxes` table for persistence
