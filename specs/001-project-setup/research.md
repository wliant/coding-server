# Research: Multi-Agent Software Development System — Initial Project Setup

**Branch**: `001-project-setup` | **Date**: 2026-03-02
**Phase 0 output for**: plan.md

---

## Topic 1: LangGraph Agent Worker Structure

### Decision
Use flat module layout with explicit submodules: `state.py`, `nodes.py`, `edges.py`, `graph.py`,
`tools.py`, `worker.py`, `config.py` inside the `worker/` package. Job intake uses a Redis `BLMOVE`
loop (crash-safe); graph execution uses `graph.astream()` for real-time progress publishing.

### Rationale
LangGraph's primitives map directly to separate files: state definitions, node functions, edge
routing, and graph assembly are each independently testable. `BLMOVE` provides crash-safe
at-most-once delivery: jobs are atomically moved to an in-flight list before processing, and any
orphaned job is recoverable at worker restart. `astream()` enables streaming intermediate node
outputs to Redis pub/sub, which the API backend relays to the web UI without polling.

A lightweight FastAPI health endpoint (on a separate port) runs inside the worker process via
`asyncio` lifespan, satisfying FR-005 without making the worker an RPC target.

### Graph structure for a coding job
```
START → planner_node → executor_node (tools via ToolNode) → reviewer_node → END
                            ↑__________________________|
                            (loop if reviewer requests changes)
```

### LangGraph checkpointing
Use `langgraph-checkpoint-postgres` with `thread_id=job_id` to enable resume-on-crash without
extra bookkeeping. The checkpointer is wired at graph compile time.

### Alternatives Considered
- **Celery worker**: Mature task queue, but process-based and doesn't compose with async LangGraph.
  Rejected.
- **HTTP callback (API POSTs to worker)**: Creates tight coupling; worker must be HTTP-reachable.
  Rejected.
- **LangGraph Platform / LangServe**: Hosted; incompatible with self-hosted Docker requirement.
  Rejected.
- **Single-file `agent.py`**: Fine for demos; not independently testable per concern. Rejected.

---

## Topic 2: FastMCP Multi-Server Architecture

### Decision
Use a **gateway pattern**: all tool servers are mounted under a single `FastMCP` gateway instance
(`tools/gateway.py`), exposed as one Docker service via `transport="streamable-http"` on
`0.0.0.0`. Each tool domain lives in its own module under `tools/servers/`.

### Rationale
Streamable HTTP (MCP 2025-03-26 spec) is the only viable transport for container-to-container
communication; stdio requires subprocess forking across containers (impossible). The gateway
pattern gives a single endpoint for the worker to connect to and a single Docker health check.
Tool functions are plain async Python and can be unit-tested by calling them directly without a
running server. FastMCP v2's in-process `Client(mcp)` covers integration testing of MCP protocol
paths (tool listing, schema validation, error serialization).

### Initial tool servers
- `filesystem_server.py`: read_file, write_file, list_directory, create_directory
- `git_server.py`: git_clone, git_commit, git_push, git_status, git_diff
- `shell_server.py`: run_command (sandboxed; explicit allowlist)

### Alternatives Considered
- **Separate Docker service per tool server**: More isolation, but adds N health checks and
  requires the worker to be configured with N endpoints. Overkill for 2-5 servers. Promoted to
  a future option when a server has distinct scaling needs.
- **SSE transport**: Works, but deprecated in MCP spec (March 2025). New code should not use it.
- **stdio transport**: Ruled out; cannot cross Docker container boundaries.

---

## Topic 3: OpenAPI-First Pipeline (FastAPI → Next.js)

### Decision
- FastAPI auto-generates the OpenAPI 3.1 spec via `app.openapi()`.
- A script (`api/scripts/export_openapi.py`) exports `openapi.json` to the repo root.
- `openapi.json` is committed to the repo; PRs that change API routes must include an updated spec
  (CI enforces with `git diff --exit-code openapi.json` after re-export).
- Next.js client is generated with `@hey-api/openapi-ts` + `@hey-api/client-fetch`.
- Client codegen runs as a `npm prebuild` script; generated files land in `web/src/client/`.
- Spec is validated in CI with `@redocly/cli lint`.

### Rationale
Committing `openapi.json` decouples frontend and backend development: the frontend can work from
the committed spec without needing the backend running. API contract changes are visible as diffs
in PRs, enabling explicit review. `@hey-api/openapi-ts` supports OpenAPI 3.1 natively and is
actively maintained. `openapi-typescript-codegen` (the predecessor) is abandoned.

FastAPI is the server implementation — no server stub generation is needed. FastAPI's route
definitions ARE the implementation; the spec is a derived artifact.

### Alternatives Considered
- **`openapi-typescript` (type-only)**: Zero runtime; requires hand-written fetch calls. Acceptable
  but more boilerplate. Consider if generated service layer becomes problematic.
- **`orval`**: Excellent React Query hook generation. Consider if the frontend adopts heavy
  data-fetching patterns. Overkill for an initial setup.
- **Generate spec at build time only (not committed)**: Simpler pipeline but loses PR-visible
  contract diffs and requires Python environment to run before any frontend work. Rejected.
- **`@stoplight/spectral-cli`**: Strong alternative to Redocly for spec validation; use if custom
  ruleset flexibility is needed.

---

## Topic 4: Docker Compose Multi-Environment Patterns

### Decision
Use **base + overlay merge pattern**: `compose.yaml` (base, shared definitions) plus
`compose.dev.yaml`, `compose.e2e.yaml`, `compose.prod.yaml` overlays. Port isolation between
dev and e2e is achieved via per-env `.env` files and distinct `COMPOSE_PROJECT_NAME` values.

### Health checks by service
- **PostgreSQL**: `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`
- **FastAPI**: `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"`
- **Next.js**: `node -e "require('http').get('http://localhost:3000/api/health', ...)`
- **LangGraph worker**: `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"` (or sentinel file if no HTTP)
- **FastMCP tools**: `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')"`
- **Redis**: `redis-cli ping`

### Startup order
A one-shot `migrate` service (Alembic `upgrade head`) runs after PostgreSQL is healthy and before
the API starts. The full dependency chain:
```
postgres (healthy) → migrate (completed) → api (healthy)
                   ↗
redis (healthy)   →  worker (healthy)
                   ↘
tools (healthy)   →
```
Frontend depends on api being healthy.

### Volume strategy
- Dev: bind mounts for source (hot reload) + `./data/postgres` + `./agent-work` (host-visible)
- E2E: anonymous volumes (ephemeral; auto-discarded after `down`)
- Prod: named Docker volumes (`postgres_data`, `agent_work`); survive `docker compose down`

### Hot reload
- FastAPI: `uvicorn --reload --reload-dir /app/src` + bind mount of `./api/src`
- Next.js: `next dev` + bind mount + anonymous `/app/node_modules` volume + `WATCHPACK_POLLING=true`

### Alternatives Considered
- **Separate fully self-contained files per env**: No duplication at start but diverges badly over
  time. Rejected.
- **Single file with Docker Compose profiles**: Profiles activate/deactivate services but cannot
  swap a service's config (e.g., bind mount → named volume). Insufficient. Rejected.
- **`wait-for-it.sh` in entrypoints**: Works but embeds orchestration inside images; hard to
  change per env. `depends_on: condition: service_healthy` is the idiomatic approach. Rejected.

---

## Topic 5: Redis Patterns for Inter-Service Communication

### Decision
- **Job queue**: `LPUSH` (backend) + `BLMOVE` (worker) — crash-safe FIFO list pattern.
- **Job live state**: Redis Hash (`HSET`/`HGETALL`) as durable source of truth, polled by the API;
  optionally enhanced with `PUBLISH` on every state change to reduce polling latency.
- **Job execution logs**: Redis List (`RPUSH`/`LRANGE`) — append-only; paginated reads.
- **TTL**: 7-day expiry set on all `job:{id}:*` keys after job completion.
- **Python client**: `redis-py >= 5.0` via `import redis.asyncio as redis` (aioredis was merged
  into redis-py in v4.2.0; the standalone aioredis package is unmaintained).
- **Testing**: `fakeredis` for unit tests (in-process, no Docker needed); `testcontainers[redis]`
  for integration tests (real Redis server).

### Key schema
```
jobs:queue             List   — pending job payloads (LPUSH/BLMOVE)
jobs:inflight          List   — jobs currently being processed (BLMOVE destination)
job:{id}:state         Hash   — status, progress, started_at, completed_at, error
job:{id}:logs          List   — append-only log entries
job:{id}:updates       Pub/Sub channel — notification signal (no persistent key)
```

### Rationale
Redis Lists provide reliable FIFO queuing for a single producer/consumer pair without the overhead
of Streams consumer groups. `BLMOVE` provides atomicity: the job is removed from `jobs:queue` and
inserted into `jobs:inflight` in one operation. At worker restart, `jobs:inflight` is drained first
to recover any orphaned jobs. The Hash pattern for job state enables `HINCRBY` for atomic progress
increments without read-modify-write races.

### Alternatives Considered
- **Redis Streams (`XADD`/`XREADGROUP`)**: Correct for multiple consumers or replay requirements.
  Overkill for single producer/consumer. Consider if the system is extended to parallel workers.
- **Pub/Sub only for status**: Messages are lost if backend is not subscribed. Rejected as sole
  mechanism; used only as an optional latency-reduction signal alongside the Hash.
- **Database polling for job status**: Would work (PostgreSQL has the job record), but adds DB
  load and 1–5s latency compared to Redis. Rejected for live status; PostgreSQL remains the
  durable record.
