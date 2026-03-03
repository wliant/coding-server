# Implementation Plan: Basic UI & Task Management

**Branch**: `002-task-management-ui` | **Date**: 2026-03-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-task-management-ui/spec.md`

## Summary

Implement the primary user interface for the Multi-Agent Software Development System: task submission, task list with search and lifecycle actions (abort/edit), and a settings page. The backend extends the existing FastAPI + PostgreSQL stack by implementing CRUD on the existing `jobs` and `projects` tables (adding two new columns and a new `settings` table), and exposing new `/tasks` and `/settings` REST routes. The frontend is built with Next.js 15 App Router, Tailwind CSS, and shadcn/ui, consuming a generated TypeScript client from the updated OpenAPI spec.

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript / Node.js 20 (web)
**Primary Dependencies**: FastAPI 0.115+ / SQLAlchemy 2 async / asyncpg / Alembic (api); Next.js 15 App Router / React 19 / Tailwind CSS / shadcn/ui / @hey-api/client-fetch (web)
**Storage**: PostgreSQL 16 — existing `jobs` and `projects` tables extended; new `settings` table added via migration `0002`
**Testing**: pytest + pytest-asyncio (api unit + integration); Jest + jsdom (web unit); Playwright (e2e)
**Target Platform**: Linux Docker containers; local dev via `compose.dev.yaml`
**Project Type**: Full-stack web application (Next.js frontend + FastAPI backend)
**Performance Goals**: Task list search results visible within 1 second for ≤500 tasks (SC-002); settings save reflected within 1 second (SC-004)
**Constraints**: No auth/authorisation in scope; agent type dropdowns are static; client-side search only
**Scale/Scope**: Up to 500 tasks (SC-007)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity-First | ✅ PASS | Extends existing stack; no new services; client-side search; static dropdowns; key-value settings table |
| II. TDD (NON-NEGOTIABLE) | ✅ PASS | Unit + integration tests for every service and route; component tests for all UI; e2e for primary flows |
| III. Modularity & Single Responsibility | ✅ PASS | Separate route modules (tasks, settings, projects), separate service classes, separate UI components per domain |
| IV. Observability | ✅ PASS | Existing JSON logger middleware captures all requests; service-layer operations emit structured INFO/ERROR entries |
| V. Incremental & Independent Delivery | ✅ PASS | 5 user stories (P1–P5) are independently implementable, testable, and demonstrable |
| VI. API-First with OpenAPI (NON-NEGOTIABLE) | ✅ PASS | `contracts/api.yaml` authored before any implementation; `openapi.json` updated as first implementation task; TS client regenerated before frontend work |

**No violations found.** No Complexity Tracking table required.

## Project Structure

### Documentation (this feature)

```text
specs/002-task-management-ui/
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
│   └── 0002_add_task_fields_and_settings.py   # new migration
└── src/api/
    ├── models/
    │   └── setting.py                          # new Setting model
    ├── schemas/
    │   ├── task.py                             # CreateTaskRequest, UpdateTaskRequest, TaskResponse
    │   ├── project.py                          # ProjectSummary
    │   └── setting.py                          # SettingsResponse, UpdateSettingsRequest
    ├── routes/
    │   ├── tasks.py                            # GET /tasks, POST /tasks, PATCH /tasks/{id}
    │   ├── projects.py                         # GET /projects (implement existing stub)
    │   └── settings.py                         # GET /settings, PUT /settings (new)
    └── services/
        ├── task_service.py                     # Task CRUD + status transition validation
        ├── project_service.py                  # Project listing + creation
        └── setting_service.py                  # Settings get/upsert with defaults
    tests/
    ├── unit/
    │   ├── test_task_service.py
    │   ├── test_project_service.py
    │   └── test_setting_service.py
    └── integration/
        ├── test_tasks_api.py
        ├── test_projects_api.py
        └── test_settings_api.py

web/
└── src/
    ├── app/
    │   ├── layout.tsx                          # updated: add Sidebar navigation
    │   ├── page.tsx                            # updated: redirect to /tasks
    │   ├── tasks/
    │   │   ├── page.tsx                        # Task list page
    │   │   ├── new/
    │   │   │   └── page.tsx                    # New task submission form
    │   │   └── [id]/
    │   │       └── edit/
    │   │           └── page.tsx                # Edit aborted task form
    │   └── settings/
    │       └── page.tsx                        # Settings page (General tab)
    └── components/
        ├── nav/
        │   └── Sidebar.tsx                     # Navigation sidebar
        ├── tasks/
        │   ├── TaskTable.tsx                   # Task list table with search + action buttons
        │   ├── TaskForm.tsx                    # Shared form (new + edit)
        │   └── AbortConfirmDialog.tsx          # Confirmation dialog for abort
        └── settings/
            └── GeneralSettings.tsx             # General tab form (agent.work.path)
    tests/
    └── unit/
        ├── TaskTable.test.tsx
        ├── TaskForm.test.tsx
        └── GeneralSettings.test.tsx
```

**Structure Decision**: Web application layout (Option 2 variant). Backend follows existing `src/` layout under `api/`; frontend follows Next.js 15 App Router conventions with collocated `components/` directory.
