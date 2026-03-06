# Implementation Plan: Automated Task Execution via Agent Worker

**Branch**: `005-requirements-feature` | **Date**: 2026-03-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-requirements-feature/spec.md`

## Summary

Implement the backend worker that automatically picks up Pending tasks, executes them using `simple_crewai_pair_agent.CodingAgent`, and tracks status via a DB-based lease pattern. Adds a task detail page to the web UI and a git push endpoint so completed code changes can be delivered to a remote repository as a new branch. Touches the API (new endpoints + migration), worker (full implementation of the polling loop), and web (new detail page + push action). The `Project.git_url` field already exists; spec 002's task form must be extended to populate it for new projects.

## Technical Context

**Language/Version**: Python 3.12 (api, worker); TypeScript / Node.js 20 (web)
**Primary Dependencies**: FastAPI 0.115+ / SQLAlchemy 2 async / asyncpg / Alembic (api); `simple_crewai_pair_agent` (worker); Next.js 15 App Router / React 19 / Tailwind CSS / shadcn/ui / @hey-api/client-fetch (web); gitpython (api, for git push operations)
**Storage**: PostgreSQL 16 — `jobs` table extended with `lease_holder` and `lease_expires_at` columns via migration `0004`; `work_directories` table unchanged
**Testing**: pytest + pytest-asyncio (api, worker); Jest + jsdom (web unit); Playwright (e2e)
**Target Platform**: Linux Docker containers; local dev via `compose.dev.yaml`
**Project Type**: Full-stack web service (Next.js + FastAPI + async worker)
**Performance Goals**: Pending task claimed within 10 s (SC-001); status visible within 10 s of change (SC-003); git push completes within 30 s (SC-004)
**Constraints**: Single-user, no auth; LLM config via env vars only; no real-time push (manual refresh); git push is force-push to task-named branch; working directory isolated per task (`AGENT_WORK_PARENT/{job_id}`)
**Scale/Scope**: Single-user; worker instances scale horizontally via lease pattern

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity-First | ✅ PASS | Extends existing stack; DB-based lease avoids Redis complexity for leasing; `gitpython` for git ops; no new services |
| II. TDD (NON-NEGOTIABLE) | ✅ PASS | Unit tests for worker polling logic, lease acquisition, agent invocation, git service; route tests for new API endpoints; component tests for task detail page |
| III. Modularity & Single Responsibility | ✅ PASS | Worker loop, lease manager, agent invoker, and git service are separate modules; API route and service layers unchanged pattern |
| IV. Observability | ✅ PASS | Worker already has JSON logging; structured log entries at task pickup, In Progress, Completed, Failed, lease renewal, push triggered, push succeeded/failed |
| V. Incremental & Independent Delivery | ✅ PASS | 3 user stories (P1–P3) independently deliverable; P1 (worker execution) is fully testable without P3 (git push) |
| VI. API-First with OpenAPI (NON-NEGOTIABLE) | ✅ PASS | `contracts/api.yaml` defines `GET /tasks/{id}` and `POST /tasks/{id}/push` before implementation; `openapi.json` updated as first implementation task; TS client regenerated before frontend work |

**No violations found.** No Complexity Tracking table required.

## Project Structure

### Documentation (this feature)

```text
specs/005-requirements-feature/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api.yaml         # OpenAPI contract for new/modified endpoints
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
api/
├── alembic/versions/
│   └── 0004_add_job_lease_fields.py          # new: lease_holder, lease_expires_at
└── src/api/
    ├── models/
    │   └── job.py                             # extend: +lease_holder, +lease_expires_at
    ├── schemas/
    │   └── task.py                            # extend: TaskDetailResponse, PushResponse, CreateTaskRequest +git_url
    ├── routes/
    │   └── tasks.py                           # extend: GET /tasks/{id}, POST /tasks/{id}/push
    └── services/
        ├── task_service.py                    # extend: get_task_detail, trigger_push
        └── git_service.py                     # new: push_working_directory_to_remote()

worker/
└── src/worker/
    ├── worker.py                              # implement: main_loop() with poll/claim/execute/complete
    ├── lease_manager.py                       # new: acquire_lease(), renew_lease(), release_lease(), reap_expired_leases()
    ├── agent_runner.py                        # new: run_coding_agent(job, work_dir) → CodingAgentResult
    └── config.py                              # extend: +POLL_INTERVAL_SECONDS, +LEASE_TTL_SECONDS, +LEASE_RENEWAL_INTERVAL_SECONDS

web/src/
├── app/
│   └── tasks/
│       └── [id]/
│           ├── page.tsx                       # new: task detail page (status, output, push action)
│           └── loading.tsx                    # new: loading skeleton
└── components/
    └── tasks/
        ├── TaskTable.tsx                      # extend: add clickable row linking to /tasks/[id]
        └── PushToRemoteButton.tsx             # new: push action button with confirmation + result display
```

**Structure Decision**: Web application layout (Next.js frontend + FastAPI backend + async worker). All new code follows the existing layered pattern: model → schema → service → route (API) and config → lease_manager → agent_runner → worker loop (worker).
