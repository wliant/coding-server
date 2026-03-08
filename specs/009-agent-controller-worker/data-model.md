# Data Model: Agent Controller / Worker Redesign

**Branch**: `009-agent-controller-worker` | **Date**: 2026-03-08

---

## 1. Main Database Changes (Migration 0009)

### 1.1 `jobs` Table — New Columns

| Column | Type | Nullable | Default | Purpose |
|---|---|---|---|---|
| `assigned_worker_id` | VARCHAR(255) | YES | NULL | Worker ID (from Controller registry) that owns this job |
| `assigned_worker_url` | VARCHAR(255) | YES | NULL | Worker base URL for proxying push/free calls |

### 1.2 `jobs.status` — Extended Values

No DB-level enum constraint exists; status is a plain string column. New values added to application layer:

| Status | Meaning | Terminal? |
|---|---|---|
| `pending` | Awaiting delegation by Controller | No |
| `in_progress` | Claimed by a worker, executing | No |
| `completed` | Agent finished successfully | No (awaits cleanup) |
| `failed` | Agent finished with error | No (awaits cleanup) |
| `aborted` | User manually aborted | Yes |
| `cleaning_up` | Cleanup initiated by user | No |
| `cleaned` | Working directory deleted, worker freed | Yes |

### 1.3 State Transition Diagram

```
pending ──(Controller claims)──► in_progress
    ▲                                │
    │ (lease expired/worker dead)    ├──(agent success)──► completed ──(user cleanup)──► cleaning_up ──► cleaned
    └────────────────────────────────│
                                     └──(agent error)───► failed ────(user cleanup)──► cleaning_up ──► cleaned

pending ──(user aborts)──► aborted   [terminal, no cleanup needed]
```

---

## 2. Worker Database Schema (New — `worker_` prefix)

### 2.1 `worker_executions` Table

| Column | Type | Nullable | Default | Purpose |
|---|---|---|---|---|
| `id` | UUID | NO | gen_random_uuid() | Primary key |
| `task_id` | UUID | NO | — | Corresponds to `jobs.id` in main DB |
| `agent_type` | VARCHAR(255) | NO | — | e.g. "simple_crewai_pair_agent" |
| `status` | VARCHAR(50) | NO | "in_progress" | in_progress / completed / failed |
| `started_at` | TIMESTAMPTZ | NO | now() | When worker started execution |
| `completed_at` | TIMESTAMPTZ | YES | NULL | When execution finished |
| `error_message` | TEXT | YES | NULL | Error detail on failure |
| `work_dir_path` | VARCHAR(1024) | NO | — | Absolute path used for this execution |

**Constraints**: UNIQUE on `task_id` (one execution record per task).

### 2.2 Worker Alembic Setup

Worker has its own `worker/alembic/` directory (separate from `api/alembic/`). Migration `worker_0001_create_worker_executions.py` creates the `worker_executions` table.

---

## 3. Controller In-Memory Registry

The Controller does not use a database for its registry. All data is held in a Python dict protected by an `asyncio.Lock`.

### 3.1 `WorkerRecord` Dataclass

```python
@dataclass
class WorkerRecord:
    worker_id: str           # UUID str, assigned by Controller on registration
    agent_type: str          # Must match an agent name in main DB agents table
    worker_url: str          # e.g. "http://worker-1:8001"
    status: str              # "free" | "in_progress" | "completed" | "failed" | "unreachable"
    last_heartbeat_at: datetime  # UTC; updated on every heartbeat
    current_task_id: str | None  # Set when worker is assigned a task
    registered_at: datetime  # UTC; set once at registration
```

### 3.2 Registry Operations

| Operation | Trigger | Effect |
|---|---|---|
| Register | Worker POSTs `/workers/register` | Add new WorkerRecord with status "free" |
| Heartbeat | Worker POSTs `/workers/{id}/heartbeat` | Update `last_heartbeat_at`; process status change if completed/failed |
| Mark unreachable | Poll cycle: heartbeat timeout exceeded | Set status "unreachable"; release task lease in DB |
| Assign task | Controller claims task in DB and calls worker | Set `current_task_id`, status "in_progress" |
| Free | Worker cleanup complete | Set `current_task_id = None`, status "free" |
| De-register | Controller restart | All records lost; workers re-register |

---

## 4. Controller's View of the Main DB

The Controller only reads/writes these tables via its own DB session:

| Table | Operations |
|---|---|
| `jobs` | READ (status=pending, agent_id); UPDATE (status, lease_holder, lease_expires_at, assigned_worker_id, assigned_worker_url, completed_at, error_message) |
| `projects` | READ (git_url, name) — included in /work payload |
| `agents` | READ (name/type) — for matching job's agent to worker's agent_type |
| `work_directories` | READ (path) — for cleanup validation only |

---

## 5. API Schemas — New and Modified

### 5.1 New: `WorkerStatus` (returned by `GET /workers`)

```json
{
  "worker_id": "string (UUID)",
  "agent_type": "string",
  "worker_url": "string",
  "status": "free | in_progress | completed | failed | unreachable",
  "current_task_id": "string (UUID) | null",
  "registered_at": "datetime (ISO 8601)",
  "last_heartbeat_at": "datetime (ISO 8601)"
}
```

### 5.2 Modified: `TaskStatus` Enum

```
pending | in_progress | completed | failed | aborted | cleaning_up | cleaned
```

### 5.3 Modified: `TaskDetailResponse`

Adds:
```json
{
  "assigned_worker_id": "string | null"
}
```

### 5.4 New: `CleanupResponse`

```json
{
  "task_id": "string (UUID)",
  "status": "cleaning_up"
}
```

---

## 6. Key Validation Rules

- `assigned_worker_id` and `assigned_worker_url` are set atomically by the Controller when claiming a job and cleared when the job reaches a terminal state (cleaned, aborted).
- A job in `cleaning_up` state cannot be re-claimed or aborted.
- A job in `cleaned` or `aborted` state cannot transition to any other status.
- Workers can only receive a new task when their `status == "free"`.
- `worker_executions.task_id` is unique — duplicate work requests for the same task are rejected by the DB constraint.
