# Developer Quickstart: Basic UI & Task Management

**Branch**: `002-task-management-ui` | **Date**: 2026-03-03

## Prerequisites

- Docker + Docker Compose installed
- `make` available
- Node.js 20+ (for local web development only)

---

## Start the dev environment

```bash
make dev
```

This starts all services with hot-reload:
- API: http://localhost:8000
- Web: http://localhost:3001
- Worker: http://localhost:8001
- Tools: http://localhost:8002

---

## Apply the new database migration

After the `0002` migration file is created, run:

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec api alembic upgrade head
```

Verify the new columns and table:

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec api \
  python -c "
from api.models.job import Job
from api.models.setting import Setting
print('dev_agent_type:', Job.dev_agent_type)
print('test_agent_type:', Job.test_agent_type)
print('Setting table:', Setting.__tablename__)
"
```

---

## Regenerate the TypeScript client (after OpenAPI spec is updated)

```bash
make generate
```

This runs `api/scripts/export_openapi.py` → writes `openapi.json` → runs `@hey-api/openapi-ts` → writes `web/src/client/`.

Always run this after any API schema change before touching frontend code.

---

## Run per-component tests

**API tests (inside container)**:
```bash
docker compose -f compose.yaml -f compose.dev.yaml exec api python -m pytest tests/ -v
```

**Web unit tests**:
```bash
docker compose -f compose.yaml -f compose.dev.yaml exec web npm test
```

**All tests**:
```bash
make test-all
```

**E2E tests**:
```bash
make e2e
```

---

## API smoke tests (manual)

Once the API is running with the migration applied:

```bash
# List tasks (should return [])
curl http://localhost:8000/tasks

# Create a task with a new project
curl -s -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "project_type": "new",
    "dev_agent_type": "spec_driven_development",
    "test_agent_type": "generic_testing",
    "requirements": "Build a hello world web page"
  }' | python -m json.tool

# Get task ID from above, then abort it
curl -s -X PATCH http://localhost:8000/tasks/<task-id> \
  -H "Content-Type: application/json" \
  -d '{ "status": "aborted" }' | python -m json.tool

# Get settings (returns defaults)
curl http://localhost:8000/settings

# Save a setting
curl -s -X PUT http://localhost:8000/settings \
  -H "Content-Type: application/json" \
  -d '{ "settings": { "agent.work.path": "/tmp/workspace" } }' | python -m json.tool
```

---

## Development order (follow task dependencies)

Implement in user story priority order. Each story is independently testable:

1. **P1 — Task Submission**: Migration → Pydantic schemas → task_service + project_service → API routes → export OpenAPI → generate TS client → TaskForm component → /tasks/new page
2. **P2 — Task List**: TaskTable component (with client-side search) → /tasks page
3. **P3 — Abort**: AbortConfirmDialog → PATCH /tasks/{id} abort → integrate into TaskTable
4. **P4 — Edit**: /tasks/[id]/edit page (reuses TaskForm) → PATCH /tasks/{id} resubmit
5. **P5 — Settings**: setting_service → /settings routes → GeneralSettings component → /settings page

Do **not** start frontend work for a story until the API routes for that story are complete and the TS client has been regenerated.

---

## Linting

```bash
# API
cd api && ruff check src/ && ruff format --check src/

# Web
cd web && npx tsc --noEmit
```

---

## Key file locations

| What | Where |
|------|-------|
| New Alembic migration | `api/alembic/versions/0002_add_task_fields_and_settings.py` |
| Job model (existing) | `api/src/api/models/job.py` |
| Setting model (new) | `api/src/api/models/setting.py` |
| Task Pydantic schemas | `api/src/api/schemas/task.py` |
| Task API routes | `api/src/api/routes/tasks.py` |
| Settings API routes | `api/src/api/routes/settings.py` |
| OpenAPI spec (source of truth) | `openapi.json` (repo root) |
| Generated TS client | `web/src/client/` (gitignored, run `make generate`) |
| Task list page | `web/src/app/tasks/page.tsx` |
| Task form | `web/src/components/tasks/TaskForm.tsx` |
| Settings page | `web/src/app/settings/page.tsx` |
