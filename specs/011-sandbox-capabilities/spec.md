# Feature Specification: Sandbox Capabilities

**Feature Branch**: `011-sandbox-capabilities`
**Created**: 2026-03-11
**Status**: Implemented
**Input**: Architectural plan for general-purpose Python execution environments (sandboxes) that provide workspace APIs, register with the controller for liveness tracking, and are visible in the UI.

## Overview

The system already has **workers** (CrewAI/LangChain agents) that register with a controller and execute coding tasks. This feature introduces a new **sandbox** concept — a general-purpose Python execution environment that provides workspace APIs (file operations, command execution, streaming logs). Sandboxes register with the controller for liveness tracking and are visible in a dedicated UI page.

Key design decisions:
- **Sandbox is a new, independent service** at `sandbox/` (port 8005), parallel to workers but serving a different purpose.
- **Labels as PostgreSQL `ARRAY(Text)`** — simpler than a join table; labels are short strings with no relational needs.
- **In-memory registry on controller** for liveness (mirrors `WorkerRegistry`), with DB persistence for labels/metadata.
- **SSE for streaming** command output (simpler than WebSocket, sufficient for stdout/stderr).
- **Controller reuses the same pattern**: register → heartbeat → reap unreachable.

---

## User Scenarios & Testing

### User Story 1 — View Registered Sandboxes (Priority: P1)

A developer navigates to the Sandboxes page in the UI to check the status of running sandbox environments. They see a table listing all registered sandboxes with their status, labels, URL, and last heartbeat time. The page auto-refreshes every 15 seconds.

**Acceptance Scenarios**:

1. **Given** a sandbox service is running and registered with the controller, **When** the user navigates to `/sandboxes`, **Then** a table is displayed showing the sandbox with status `free`, its labels (e.g., `python`, `git`), URL, and last heartbeat timestamp.
2. **Given** multiple sandboxes are registered, **When** the user views the Sandboxes page, **Then** all sandboxes are listed in the table.
3. **Given** a sandbox has stopped sending heartbeats for more than 60 seconds, **When** the controller runs its poll cycle, **Then** the sandbox is marked `unreachable` and the UI reflects this with a red status badge.
4. **Given** no sandboxes are registered, **When** the user navigates to `/sandboxes`, **Then** a message "No sandboxes registered. Start a sandbox service to see it here." is displayed.

---

### User Story 2 — Execute Commands in Sandbox (Priority: P1)

A developer or automated system sends commands to a sandbox for execution. The sandbox runs the command in its workspace directory and returns the result (exit code, stdout, stderr).

**Acceptance Scenarios**:

1. **Given** a running sandbox, **When** `POST /execute` is called with `{"command": "python --version"}`, **Then** the response contains `exit_code: 0` and stdout with the Python version string.
2. **Given** a running sandbox, **When** `POST /execute` is called with a command that fails, **Then** the response contains a non-zero `exit_code` and the error in `stderr`.
3. **Given** a running sandbox, **When** `POST /execute` is called with a command that exceeds the timeout, **Then** the process is killed and the response contains `exit_code: -1` with a timeout error message in `stderr`.

---

### User Story 3 — Manage Files in Sandbox Workspace (Priority: P1)

A developer or automated system manages files within the sandbox workspace using REST APIs — listing, reading, writing, deleting files, and creating directories.

**Acceptance Scenarios**:

1. **Given** a running sandbox, **When** `PUT /files/test.py` is called with `{"content": "print('hello')"}`, **Then** the file is created in the workspace and a subsequent `GET /files/test.py` returns its content.
2. **Given** files exist in the workspace, **When** `GET /files` is called, **Then** a recursive listing of all files and directories is returned (excluding `.git`).
3. **Given** a file exists, **When** `DELETE /files/test.py` is called, **Then** the file is removed and a subsequent `GET /files/test.py` returns 404.
4. **Given** a path that resolves outside the workspace, **When** any file operation is attempted, **Then** a 403 error is returned.
5. **Given** a running sandbox, **When** `POST /mkdir/src/utils` is called, **Then** the directory is created recursively.
6. **Given** a running sandbox, **When** `GET /download` is called, **Then** a zip archive of the workspace is returned (excluding `.git` directories).

---

### User Story 4 — Stream Command Output (Priority: P2)

A developer wants to see real-time output from a long-running command. The sandbox supports SSE (Server-Sent Events) streaming of stdout and stderr lines.

**Acceptance Scenarios**:

1. **Given** a running sandbox, **When** `POST /execute/stream` is called with a command, **Then** SSE events are streamed with `event: stdout` and `event: stderr` types, followed by an `event: exit` with the exit code.
2. **Given** a streaming command that exceeds the timeout, **Then** an `event: error` is sent with a timeout message.

---

### Edge Cases

- What happens when the sandbox is unreachable but the UI still shows it? The controller's reap cycle marks it `unreachable` within 60 seconds.
- What happens when a file operation targets a binary file for reading? A 400 error is returned with "Binary file — use /download instead".
- What happens when a file exceeds 500 KB? The content is truncated with a warning prefix.
- What happens when the controller restarts? The sandbox's heartbeat loop detects a 404 and automatically re-registers.

---

## Requirements

### Functional Requirements

- **FR-001**: The system MUST support a new `sandboxes` database table with columns: `id` (UUID PK), `sandbox_id` (unique string), `sandbox_url`, `ip_address`, `status` (free/allocated/unavailable), `labels` (ARRAY(Text)), `created_at`, `updated_at`, `last_heartbeat_at`.
- **FR-002**: The controller MUST maintain an in-memory `SandboxRegistry` (mirroring `WorkerRegistry`) that tracks registered sandboxes with their status and liveness.
- **FR-003**: The controller MUST expose `POST /sandboxes/register` to accept sandbox registrations with `sandbox_id`, `sandbox_url`, and `labels`.
- **FR-004**: The controller MUST expose `POST /sandboxes/{sandbox_id}/heartbeat` to accept status updates; it MUST return 404 if the sandbox is not registered (triggering re-registration).
- **FR-005**: The controller MUST expose `GET /sandboxes` returning all registered sandboxes with their status, labels, and timing information.
- **FR-006**: The controller's delegator loop MUST reap sandboxes whose last heartbeat exceeds `SANDBOX_HEARTBEAT_TIMEOUT_SECONDS` (default 60s), marking them `unreachable` in both registry and database.
- **FR-007**: The main API MUST expose `GET /sandboxes` as a proxy route to the controller's `/sandboxes` endpoint (same pattern as `GET /workers`).
- **FR-008**: The sandbox service MUST register with the controller on startup and send periodic heartbeats, with automatic re-registration on 404.
- **FR-009**: The sandbox service MUST expose workspace file APIs: `GET /files` (recursive listing), `GET /files/{path}` (read), `PUT /files/{path}` (write), `DELETE /files/{path}` (delete), `POST /mkdir/{path}` (create directory).
- **FR-010**: The sandbox service MUST expose `GET /download` returning the workspace as a zip archive.
- **FR-011**: The sandbox service MUST expose `POST /execute` for synchronous command execution returning `{exit_code, stdout, stderr}`.
- **FR-012**: The sandbox service MUST expose `POST /execute/stream` for SSE streaming of command output with `stdout`, `stderr`, `exit`, and `error` event types.
- **FR-013**: All file operations MUST validate that resolved paths are within the workspace directory; paths outside MUST be rejected with 403.
- **FR-014**: The web UI MUST include a `/sandboxes` page showing a table of all sandboxes with columns: Sandbox ID, Status (badge), Labels (pills), URL, Last Heartbeat (relative time).
- **FR-015**: The sidebar navigation MUST include a "Sandboxes" link between "Workers" and "Settings".

### Non-Functional Requirements

- **NFR-001**: The sandbox service MUST be containerized as a standalone Docker image based on `python:3.12-slim`.
- **NFR-002**: The sandbox container MUST include `git`, `curl`, `jq`, and `build-essential` for general-purpose development work.
- **NFR-003**: The sandbox MUST run as a non-root user (`appuser`) with ownership of the `/workspace` directory.
- **NFR-004**: Command execution MUST support configurable timeouts (default 300s) to prevent runaway processes.
- **NFR-005**: File content reads MUST truncate at 500 KB with a warning prefix for large files.
- **NFR-006**: The Sandboxes page MUST auto-refresh every 15 seconds.

---

## Key Entities

### Sandbox (Database)

| Field              | Type           | Nullable | Notes |
|--------------------|----------------|----------|-------|
| `id`               | UUID (PK)      | No       | Auto-generated |
| `sandbox_id`       | String(255)    | No       | Unique; proposed by sandbox on registration |
| `sandbox_url`      | String(255)    | No       | Externally-reachable URL (e.g., `http://sandbox:8005`) |
| `ip_address`       | String(45)     | Yes      | IPv4/IPv6 address |
| `status`           | String(20)     | No       | `free`, `allocated`, `unavailable`, `unreachable` |
| `labels`           | ARRAY(Text)    | Yes      | Capability tags (e.g., `["python", "git"]`) |
| `created_at`       | DateTime (tz)  | No       | First registration time |
| `updated_at`       | DateTime (tz)  | No       | Last modification time |
| `last_heartbeat_at`| DateTime (tz)  | No       | Last successful heartbeat |

### SandboxRecord (In-Memory Registry)

| Field              | Type           | Notes |
|--------------------|----------------|-------|
| `sandbox_id`       | str            | Unique identifier |
| `sandbox_url`      | str            | Service URL |
| `labels`           | list[str]      | Capability tags |
| `status`           | SandboxStatus  | `free`, `allocated`, `unavailable`, `unreachable` |
| `last_heartbeat_at`| datetime       | UTC timestamp |
| `registered_at`    | datetime       | UTC timestamp |

### ExecutionResult

| Field       | Type    | Notes |
|-------------|---------|-------|
| `exit_code` | int     | Process exit code; -1 on timeout |
| `stdout`    | str     | Captured standard output |
| `stderr`    | str     | Captured standard error |

---

## Architecture

### Service Topology

```
┌─────────┐     ┌────────────┐     ┌─────────────────┐
│   Web   │────▶│  Main API  │────▶│   Controller    │
│ :3000   │     │  :8000     │     │   :8003         │
└─────────┘     └────────────┘     │                 │
                                   │  WorkerRegistry │
                                   │  SandboxRegistry│
                                   └─────┬───────────┘
                                         │
                           ┌─────────────┼─────────────┐
                           │             │             │
                     ┌─────▼─────┐ ┌─────▼─────┐ ┌────▼──────┐
                     │  Worker   │ │  Worker   │ │  Sandbox  │
                     │  :8001   │ │  :8004   │ │  :8005    │
                     └───────────┘ └───────────┘ └───────────┘
```

### Registration Flow

```
Sandbox startup:
  1. POST /sandboxes/register → Controller
     Body: { sandbox_id, sandbox_url, labels }
     Response: { sandbox_id }
  2. Controller stores in SandboxRegistry (in-memory)
  3. Controller upserts to sandboxes table (DB)

Heartbeat loop (every 15s):
  1. POST /sandboxes/{sandbox_id}/heartbeat → Controller
     Body: { status: "free" }
  2. If 404: re-register (controller restarted)

Reap cycle (every 10s poll):
  1. Controller checks all sandboxes in registry
  2. If last_heartbeat_at > 60s ago → mark "unreachable"
  3. Update DB status to "unreachable"
```

### Workspace API Endpoints

| Endpoint                  | Method | Description |
|---------------------------|--------|-------------|
| `GET /health`             | GET    | Health check |
| `GET /files`              | GET    | List files recursively (query param: `path`) |
| `GET /files/{path:path}`  | GET    | Read file content |
| `PUT /files/{path:path}`  | PUT    | Write file (body: `{content}`) |
| `DELETE /files/{path:path}` | DELETE | Delete file or directory |
| `POST /mkdir/{path:path}` | POST   | Create directory (recursive) |
| `GET /download`           | GET    | Download workspace as zip archive |
| `POST /execute`           | POST   | Run command, return `{exit_code, stdout, stderr}` |
| `POST /execute/stream`    | POST   | Run command, SSE stream of stdout/stderr lines |

---

## Success Criteria

- **SC-001**: The sandbox service starts, registers with the controller, and appears in `GET /sandboxes` with status `free` within 30 seconds of container start.
- **SC-002**: Stopping the sandbox container results in the controller marking it `unreachable` within 60 seconds.
- **SC-003**: `POST /execute` with `{"command": "python --version"}` returns exit code 0 and the Python version in stdout.
- **SC-004**: File CRUD operations (write, read, list, delete) work correctly on the `/workspace` directory.
- **SC-005**: `GET /download` returns a valid zip archive of workspace contents.
- **SC-006**: The `/sandboxes` UI page displays all registered sandboxes with correct status badges and label pills.
- **SC-007**: The sandbox automatically re-registers with the controller after a controller restart (heartbeat returns 404).

---

## Implementation Details

### New Files

| File | Purpose |
|------|---------|
| `api/src/api/models/sandbox.py` | Sandbox ORM model (UUID PK, sandbox_id unique, ARRAY labels) |
| `api/alembic/versions/0011_add_sandboxes_table.py` | Migration: create `sandboxes` table |
| `api/src/api/schemas/sandbox.py` | Pydantic `SandboxStatus` response schema |
| `api/src/api/routes/sandboxes.py` | `GET /sandboxes` proxy route to controller |
| `agents-controller/src/controller/sandbox_registry.py` | `SandboxRegistry` class (register, heartbeat, reap) |
| `sandbox/Dockerfile` | Python 3.12-slim + git, curl, jq, build-essential; non-root user |
| `sandbox/pyproject.toml` | Package: fastapi, uvicorn, httpx, pydantic-settings, python-json-logger |
| `sandbox/src/sandbox/__init__.py` | Package init |
| `sandbox/src/sandbox/app.py` | FastAPI app with lifespan (register + heartbeat loop) |
| `sandbox/src/sandbox/config.py` | Settings: CONTROLLER_URL, SANDBOX_PORT, LABELS, WORKSPACE_DIR, timeouts |
| `sandbox/src/sandbox/registration.py` | `register_with_controller()` + `start_heartbeat_loop()` |
| `sandbox/src/sandbox/executor.py` | `execute_command()` (sync) + `stream_command()` (SSE async generator) |
| `sandbox/src/sandbox/routes.py` | Workspace API: file CRUD, mkdir, download, execute, stream |
| `web/src/app/sandboxes/page.tsx` | Sandboxes list page (client component, auto-refresh 15s) |
| `web/src/components/sandboxes/SandboxesTable.tsx` | Table with status badges + label pills |

### Modified Files

| File | Changes |
|------|---------|
| `api/src/api/db.py` | Import `Sandbox` model to register with Base metadata |
| `api/src/api/main.py` | Include `sandboxes_router` |
| `agents-controller/src/controller/routes.py` | Add `SandboxRegistry` param to `make_router()`; add sandbox register/heartbeat/list endpoints |
| `agents-controller/src/controller/models.py` | Add `Sandbox` ORM model (mirrors API model for DB upserts) |
| `agents-controller/src/controller/delegator.py` | Add `_reap_unreachable_sandboxes()`; integrate into `run_poll_cycle()` |
| `agents-controller/src/controller/app.py` | Create `SandboxRegistry` in `create_app()`; pass to router and delegator |
| `agents-controller/src/controller/config.py` | Add `SANDBOX_HEARTBEAT_TIMEOUT_SECONDS: int = 60` |
| `compose.yaml` | Add `sandbox` service (port 8005, depends on controller healthy) |
| `compose.dev.yaml` | Add sandbox dev overrides (port mapping, volume mount, CORS) |
| `openapi.json` | Add `GET /sandboxes` operation + `SandboxStatus` schema |
| `web/src/components/nav/Sidebar.tsx` | Add "Sandboxes" nav link between Workers and Settings |

### Database Migration (0011)

Creates `sandboxes` table:
```sql
CREATE TABLE sandboxes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id VARCHAR(255) NOT NULL UNIQUE,
    sandbox_url VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    status VARCHAR(20) NOT NULL DEFAULT 'free',
    labels TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Docker Compose Configuration

**compose.yaml** (production):
```yaml
sandbox:
  build:
    context: ./sandbox
  expose: ["8005"]
  environment:
    CONTROLLER_URL: http://controller:8003
    SANDBOX_PORT: "8005"
    LABELS: "python,git"
    WORKSPACE_DIR: /workspace
  networks: [backend]
  depends_on:
    controller: { condition: service_healthy }
  healthcheck:
    test: python -c "import urllib.request; urllib.request.urlopen('http://localhost:8005/health')"
```

**compose.dev.yaml** (development overrides):
```yaml
sandbox:
  ports: ["${SANDBOX_PORT:-8005}:8005"]
  volumes: ["./sandbox/src:/app/src"]
  environment:
    PYTHONPATH: /app/src
    CORS_ORIGINS: "http://localhost:3000"
```

---

## Verification Checklist

1. `docker compose build sandbox migrate api controller` — all images build
2. `task dev` — sandbox registers with controller (check controller logs for `sandbox_registered`)
3. `GET http://localhost:8003/sandboxes` — returns sandbox with status=free
4. `GET http://localhost:8000/sandboxes` — proxy returns same data
5. Stop sandbox container → after 60s, controller marks it unreachable
6. Test workspace APIs on sandbox directly:
   - `POST http://localhost:8005/execute` with `{"command": "python --version"}`
   - `PUT http://localhost:8005/files/test.py` with `{"content": "print('hello')"}`
   - `GET http://localhost:8005/files/test.py` — returns content
   - `GET http://localhost:8005/files` — lists test.py
   - `DELETE http://localhost:8005/files/test.py`
   - `POST http://localhost:8005/mkdir/src`
   - `GET http://localhost:8005/download` — returns zip
   - `POST http://localhost:8005/execute/stream` — SSE stream
7. Open `http://localhost:3000/sandboxes` — see sandbox in table with status badge and labels

---

## Assumptions

- A single sandbox instance is deployed in the default compose configuration; horizontal scaling (multiple sandboxes) is supported by the registry design but not configured by default.
- Sandboxes are stateless from the controller's perspective — they have no assigned tasks or job lifecycle. The `allocated` status is reserved for future use when sandboxes are assigned to specific tasks or users.
- The `/workspace` directory is ephemeral within the container; persistent workspace storage requires volume configuration.
- Command execution uses `asyncio.create_subprocess_shell` — commands run as the `appuser` user inside the container.
- Labels are informational tags (e.g., `python`, `git`, `node`) describing available tools; they are not used for routing decisions in the current implementation.
- The SSE streaming endpoint (`POST /execute/stream`) collects stdout and stderr in parallel and emits them as separate event types; line ordering between streams is not guaranteed.
