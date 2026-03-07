# Implementation Plan: Enhanced Task Submission

**Branch**: `006-enhance-task-submission` | **Date**: 2026-03-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-enhance-task-submission/spec.md`

## Summary

Replace the dual Dev Agent / Test Agent fields with a single database-backed agent selector, add full project selection (new vs existing), project naming, and git URL support to the task submission form, and enable users to add a git URL to a completed task and trigger a push. The implementation adds a new `agents` registry table, two Alembic migrations, a `GET /agents` endpoint, updates `POST /tasks` and `POST /tasks/{id}/push`, and replaces the web form fields accordingly.

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript / Node.js 20 (web)
**Primary Dependencies**: FastAPI 0.115+, SQLAlchemy 2 async, Alembic, asyncpg, Pydantic v2 (api); Next.js 15 App Router, React 19, Tailwind CSS, shadcn/ui, @hey-api/client-fetch (web)
**Storage**: PostgreSQL 16 — new `agents` table via migration 0005; nullable `agent_id` FK on `jobs` via migration 0006; no changes to `projects` table schema
**Testing**: pytest + pytest-asyncio (api, asyncio_mode=auto); Playwright (e2e)
**Target Platform**: Linux server (Docker)
**Project Type**: web-service (FastAPI backend) + web-application (Next.js frontend)
**Performance Goals**: <200ms p95 for API responses (inherited from existing system)
**Constraints**: Backward-compatible deprecation — `dev_agent_type`/`test_agent_type` columns remain in DB and API responses; existing tasks are unaffected
**Scale/Scope**: Same as existing system; agent registry is expected to hold O(10) rows

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity-First | ✅ PASS | One new DB table, two migrations, one new route module. No new services, no new infrastructure patterns. |
| II. TDD (NON-NEGOTIABLE) | ✅ PASS | Test tasks are generated before implementation tasks in every phase. Red-Green-Refactor cycle enforced in tasks.md. |
| III. Modularity & Single Responsibility | ✅ PASS | New `agents` route is a separate module. Contracts live in `contracts/api.yaml`. No cross-module implementation detail dependencies. |
| IV. Observability | ✅ PASS | Existing structured logging patterns in api and worker are followed. New endpoint logs follow the same INFO/ERROR conventions. |
| V. Incremental & Independent Delivery | ✅ PASS | US1 (new project), US2 (existing project), and US3 (push with URL) are independently deliverable. US1 can ship as MVP before US2/US3. |
| VI. API-First with OpenAPI (NON-NEGOTIABLE) | ✅ PASS | `contracts/api.yaml` (version 0.3.0) is the first implementation task (T001). `openapi.json` is updated and `task generate` regenerates the TypeScript client before any business logic is written. |

*Post-Phase-1 re-check*: All gates still pass. No new violations introduced by data model or contract design.

## Project Structure

### Documentation (this feature)

```text
specs/006-enhance-task-submission/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── api.yaml         # OpenAPI 0.3.0 contract
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
api/
├── alembic/versions/
│   ├── 0005_add_agents_table.py         # NEW: create agents table + seed
│   └── 0006_add_agent_id_to_jobs.py     # NEW: nullable agent_id FK on jobs
├── src/api/
│   ├── models/
│   │   └── agent.py                     # NEW: Agent ORM model
│   ├── schemas/
│   │   ├── agent.py                     # NEW: AgentSummary, AgentResponse
│   │   └── task.py                      # MODIFIED: deprecations, agent_id, project_name, PushTaskRequest
│   ├── routes/
│   │   ├── agents.py                    # NEW: GET /agents
│   │   └── tasks.py                     # MODIFIED: push body param, agent join
│   └── services/
│       └── task_service.py              # MODIFIED: agent_id handling, push git_url save
└── tests/
    ├── unit/                            # NEW: agent schema validation tests
    └── integration/                     # NEW: GET /agents, POST /tasks with agent_id

openapi.json                             # MODIFIED: version 0.3.0 (regenerated via task generate)

web/
├── src/
│   ├── client/                          # REGENERATED: from updated openapi.json
│   └── components/tasks/
│       ├── TaskForm.tsx                 # MODIFIED: agent dropdown, project name field, git URL field
│       └── TaskDetail.tsx               # MODIFIED: git URL input + push for US3
└── tests/                               # NEW: e2e tests for US1, US2, US3
```

**Structure Decision**: Single-project layout (existing pattern). All changes are additive within the established `api/` and `web/` directories. No new top-level projects or Docker services are required.

## Complexity Tracking

> No constitution violations. This section is intentionally empty.
