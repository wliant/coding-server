# Implementation Plan: Multi-Agent Software Development System — Initial Project Setup

**Branch**: `001-project-setup` | **Date**: 2026-03-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-project-setup/spec.md`

## Summary

Establish the complete four-component repository scaffold (web interface, API backend, agent worker,
MCP tool servers) with Docker Compose environments for local development, end-to-end testing, and
production. All components run as containers; PostgreSQL provides persistent storage; Redis handles
the job queue and cross-component live state. The backend REST API is defined as an OpenAPI 3.1
contract before any implementation code is written, with a TypeScript client generated for the
Next.js frontend.

## Technical Context

**Language/Version**: Python 3.12 (api, worker, tools); TypeScript / Node.js 20 (web)
**Primary Dependencies**:
- web: Next.js 15, @hey-api/openapi-ts, @hey-api/client-fetch
- api: FastAPI 0.115+, SQLAlchemy 2.x (async), Alembic, redis-py 5+, uvicorn
- worker: LangGraph 0.2+, langchain-mcp-adapters, FastAPI (health only), redis-py 5+
- tools: FastMCP 2.x, pytest-asyncio
- infra: PostgreSQL 16, Redis 7

**Storage**: PostgreSQL 16 (primary persistence — projects, jobs, work directory metadata);
Redis 7 (job queue via List BLMOVE, live job state via Hash, execution logs via List)

**Testing**: pytest + pytest-asyncio + fakeredis (unit, Python components);
testcontainers[redis/postgres] (integration); Playwright (e2e web flows)

**Target Platform**: Linux server, Docker Compose (single-host deployment)

**Project Type**: Multi-component containerized web application (4 app services + 2 infra services)

**Performance Goals**: Single user; one job at a time; no concurrency requirements.
Developer startup time ≤ 5 minutes (SC-001).

**Constraints**: Sequential job processing; agent work directories isolated per job; no external
authentication needed (single-user, network-restricted)

**Scale/Scope**: 1 user, 4 app components, 3 environments (dev / e2e / prod)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status | Notes |
|-----------|------|--------|-------|
| I. Simplicity-First | All complexity justified in Complexity Tracking | ✅ PASS | 4-component architecture explicitly required by spec; justification below |
| II. TDD (NON-NEGOTIABLE) | Tests written before implementation code | ✅ PASS | pytest mandated (FR-010); e2e environment in spec (FR-003); enforced in tasks.md |
| III. Modularity | Each component has one role; contracts defined for all inter-component interfaces | ✅ PASS | OpenAPI (web↔api); MCP protocol (worker↔tools); Redis queue+hash (api↔worker) |
| IV. Observability | Health endpoints on all 4 services; structured logging in all components | ✅ PASS | FR-005 mandates health endpoints; JSON structured logs required in all Python services |
| V. Incremental Delivery | 4 user stories, each independently testable | ✅ PASS | US1→US2→US3→US4 each have explicit independent test criteria |
| VI. API-First with OpenAPI (NON-NEGOTIABLE) | OpenAPI spec authored before backend implementation; client generated from spec | ✅ PASS | `contracts/openapi.yaml` produced in this plan; @hey-api/openapi-ts generates Next.js client; MCP and Redis interfaces are not REST (no OpenAPI needed) |

**Post-Phase-1 re-check**: All gates confirmed. OpenAPI contract is in `contracts/openapi.yaml`.

## Project Structure

### Documentation (this feature)

```text
specs/001-project-setup/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── openapi.yaml     # Phase 1 output — backend REST API contract
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
coding-machine/
├── compose.yaml               # Base Docker Compose (shared service definitions)
├── compose.dev.yaml           # Dev overrides: bind mounts, hot reload, host ports
├── compose.e2e.yaml           # E2E test overrides: isolated ports, ephemeral volumes
├── compose.prod.yaml          # Prod overrides: named volumes, restart policies, no debug
├── .env                       # Dev environment defaults (COMPOSE_PROJECT_NAME, ports)
├── .env.e2e                   # E2E environment overrides (port offsets, project name)
├── openapi.json               # Committed OpenAPI spec (exported from FastAPI; source of truth for client gen)
├── Makefile                   # Top-level commands: make dev, make e2e, make generate
│
├── web/                       # Next.js web interface
│   ├── src/
│   │   ├── app/               # Next.js App Router
│   │   │   ├── page.tsx
│   │   │   ├── layout.tsx
│   │   │   └── api/
│   │   │       └── health/
│   │   │           └── route.ts
│   │   ├── client/            # Generated API client (from openapi.json via @hey-api/openapi-ts)
│   │   └── components/        # UI components
│   ├── tests/
│   │   ├── e2e/               # Playwright end-to-end tests
│   │   └── unit/              # Jest unit tests
│   ├── openapi-ts.config.ts   # Client codegen config
│   ├── Dockerfile
│   └── package.json
│
├── api/                       # FastAPI REST API backend
│   ├── src/
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── main.py        # FastAPI app + lifespan
│   │       ├── routes/
│   │       │   ├── health.py
│   │       │   ├── projects.py
│   │       │   └── jobs.py
│   │       ├── models/        # SQLAlchemy ORM models
│   │       │   ├── project.py
│   │       │   └── job.py
│   │       ├── schemas/       # Pydantic request/response schemas
│   │       │   ├── project.py
│   │       │   └── job.py
│   │       ├── services/
│   │       │   ├── job_service.py
│   │       │   └── redis_client.py
│   │       └── db.py          # Async SQLAlchemy session + engine
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── scripts/
│   │   └── export_openapi.py  # Exports app.openapi() → openapi.json at repo root
│   ├── Dockerfile
│   └── pyproject.toml
│
├── worker/                    # LangGraph agent worker
│   ├── src/
│   │   └── worker/
│   │       ├── __init__.py
│   │       ├── state.py       # AgentState TypedDict + Annotated reducers
│   │       ├── nodes.py       # Async node functions
│   │       ├── edges.py       # Routing/conditional edge functions
│   │       ├── graph.py       # StateGraph assembly + compile()
│   │       ├── tools.py       # MCP ClientSession + load_mcp_tools()
│   │       ├── worker.py      # BLMOVE job loop + FastAPI health app
│   │       └── config.py      # Pydantic Settings (env vars)
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_nodes.py
│   │   │   ├── test_edges.py
│   │   │   └── test_tools.py
│   │   ├── integration/
│   │   │   └── test_graph.py
│   │   └── conftest.py
│   ├── Dockerfile
│   └── pyproject.toml
│
└── tools/                     # FastMCP tool servers
    ├── src/
    │   └── tools/
    │       ├── __init__.py
    │       ├── servers/
    │       │   ├── __init__.py
    │       │   ├── filesystem_server.py
    │       │   ├── git_server.py
    │       │   └── shell_server.py
    │       └── gateway.py     # Mounts all servers; entry point
    ├── tests/
    │   ├── unit/
    │   │   ├── test_filesystem_server.py
    │   │   ├── test_git_server.py
    │   │   └── test_shell_server.py
    │   ├── integration/
    │   │   └── test_gateway.py
    │   └── conftest.py
    ├── Dockerfile
    └── pyproject.toml
```

**Structure Decision**: Multi-component web application (Option 2 variant, extended to 4 app
services). Each component has its own `src/` (src-layout) and `tests/` peer directory, enforcing
clean prod/test separation (FR-009, SC-005). Docker Compose files live at the repository root for
single-command orchestration. `openapi.json` is committed at the root and regenerated by
`make generate` whenever backend routes change.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| 4 application components (web, api, worker, tools) | Each serves a distinct role that cannot share a runtime. Long-running LLM jobs in the worker would block HTTP request threads in the API. MCP tool servers must be independently restartable (FR-014). The web interface requires a different language runtime (Node.js). | A monolith would merge incompatible runtimes, block the API on agent jobs, and prevent independent restart of tool servers. No fewer than 4 components can satisfy all spec requirements. |
| 2 infrastructure services (postgres + redis) | PostgreSQL is explicitly required for relational persistence (FR-006, spec assumptions). Redis is explicitly required for cross-component state sharing (FR-007, spec assumptions). | Eliminating redis would require polling the database for job status, adding unnecessary DB load and latency. Eliminating postgres would lose durable persistence and transactional safety. |
