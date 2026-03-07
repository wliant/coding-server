# Implementation Plan: GitHub Token Integration

**Branch**: `008-github-token` | **Date**: 2026-03-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-github-token/spec.md`

## Summary

Add GitHub Personal Access Token support to the system: a new **GitHub** tab in Settings stores the token, the worker uses it to **clone** the project repository before running the coding agent (optionally on a user-specified branch, creating the branch if it doesn't exist remotely), and the API uses it to **authenticate pushes** when pushing completed work back to GitHub.

Technical approach: token embedded in HTTPS URL for GitPython operations; new `branch` column on `jobs` table; new `git_utils.py` in worker for clone logic; settings key `github.token`; new `GitHubSettings` React component.

## Technical Context

**Language/Version**: Python 3.12 (api, worker) · TypeScript / Node.js 20 (web)
**Primary Dependencies**: FastAPI 0.115+, SQLAlchemy 2 async, GitPython 3.1+ (api + worker), Alembic (api); Next.js 15, React 19, shadcn/ui (web)
**Storage**: PostgreSQL 16 — `jobs` table extended; `settings` table key-value extended
**Testing**: pytest + pytest-asyncio (`asyncio_mode = "auto"`) for api/worker; TypeScript `tsc --noEmit` + existing test setup for web
**Target Platform**: Linux (Docker containers, `compose.yaml`)
**Project Type**: Web service (FastAPI API + worker) + web frontend (Next.js)
**Performance Goals**: Standard sub-second API responses; clone time is bounded by repository size (no enforced timeout in this feature)
**Constraints**: Token stored as plain text in `settings` table, consistent with OpenAI/Anthropic key handling; SSH URLs fall back to system key behavior (no token injection)
**Scale/Scope**: Single-user / small team; single global GitHub token across all projects

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity-First | ✅ PASS | Reuses settings infrastructure; URL-embedding for auth (no new auth framework); no new service abstractions |
| II. TDD (NON-NEGOTIABLE) | ✅ PASS | Tests written before implementation for each user story |
| III. Modularity | ✅ PASS | Clone logic isolated in `worker/src/worker/git_utils.py`; `GitHubSettings` component is self-contained; `git_service.py` unchanged |
| IV. Observability | ✅ PASS | Structured log events required: `clone_started`, `clone_succeeded`, `clone_failed` (with `job_id`, `git_url`, `branch`); token MUST NOT appear in logs |
| V. Incremental Delivery | ✅ PASS | 3 independently deliverable stories; Story 1 (settings) can ship alone |
| VI. API-First with OpenAPI (NON-NEGOTIABLE) | ✅ PASS | `openapi.json` updated and TS client regenerated before any frontend code |

**No violations** — Complexity Tracking table not required.

## Project Structure

### Documentation (this feature)

```text
specs/008-github-token/
├── plan.md              # This file
├── research.md          # Phase 0 findings
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 quickstart
├── contracts/
│   └── openapi-changes.md   # Phase 1 contract changes
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code Changes

```text
openapi.json                                     # Update first: branch field + version bump

api/
├── alembic/versions/
│   └── 0008_add_branch_to_jobs.py               # NEW: adds branch column to jobs
└── src/api/
    ├── models/
    │   └── job.py                               # Add: branch Mapped[str | None]
    ├── schemas/
    │   └── task.py                              # Add: branch field to CreateTaskRequest + TaskDetailResponse
    └── services/
        ├── setting_service.py                   # Add: github.token to ALLOWED_KEYS + DEFAULTS
        └── task_service.py                      # Add: token injection in trigger_push()

worker/
├── pyproject.toml                               # Add: gitpython>=3.1 dependency
└── src/worker/
    ├── git_utils.py                             # NEW: clone_repository() + inject_github_token()
    ├── models.py                                # Add: branch column to Job model
    └── agent_runner.py                          # Add: clone step before CodingAgent invocation

web/
├── src/
│   ├── app/settings/page.tsx                   # Add: GitHub tab (third tab)
│   └── components/settings/
│       └── GitHubSettings.tsx                  # NEW: GitHub token field component
└── src/client/                                  # Regenerated (npm run generate)

api/tests/                                       # New/updated tests for task schema + push auth
worker/tests/                                    # New tests for git_utils.py + agent_runner clone
```

## Implementation Order (Story-by-Story)

### Story 1 — GitHub Token in Settings (P1, foundation)

**Touches**: `openapi.json`, `setting_service.py`, `web/settings/page.tsx`, `GitHubSettings.tsx`

1. Update `openapi.json` — add `github.token` to settings description; bump version to `0.5.0`
2. Run `cd web && npm run generate`
3. Add `github.token` to `ALLOWED_KEYS` + `DEFAULTS` in `setting_service.py`
4. Write API tests: GET /settings returns `github.token`; PUT /settings accepts/rejects token values
5. Create `GitHubSettings.tsx` — masked token field; same Props pattern as `AgentSettings`
6. Add GitHub tab to `web/src/app/settings/page.tsx`
7. Verify UI: enter token → save → refresh → masked display

### Story 2 — Clone Repository Before Agent Starts (P2)

**Touches**: `openapi.json`, `task.py` schemas, `job.py` model, `0008` migration, worker `models.py`, `git_utils.py`, `agent_runner.py`

1. Update `openapi.json` — add `branch` to `CreateTaskRequest` + `TaskDetailResponse`; bump version
2. Run `cd web && npm run generate`
3. Write migration `0008_add_branch_to_jobs.py`
4. Add `branch` to `api/src/api/models/job.py` + `api/src/api/schemas/task.py`
5. Add `branch` to `worker/src/worker/models.py`
6. Update `task_service.create_task()` to save `branch` from request
7. Add `gitpython>=3.1` to `worker/pyproject.toml`
8. Write and test `worker/src/worker/git_utils.py` (unit tests with tmp dirs)
9. Update `agent_runner.run_coding_agent()` to call `clone_repository()` when `project.git_url` is set; emit structured log events; fail task on clone error
10. Integration test: task with git_url → verify work dir has cloned content

### Story 3 — Authenticated Push (P3)

**Touches**: `task_service.py`, (optionally a helper extracted to `api/src/api/services/git_utils.py`)

1. Add `_inject_github_token(url, token)` helper in `task_service.py`
2. In `trigger_push()`: fetch settings, inject token if GitHub HTTPS URL
3. Test: push with mocked settings returns authenticated URL to `git_service`
4. Manual verification: push to private GitHub repo succeeds

## Key Design Decisions (from research.md)

- **Token injection**: URL embedding (`https://{token}@github.com/...`) — simplest, no system config
- **Branch fallback**: clone default → `create_head(branch)` → checkout — two-phase, single git call path
- **Clone location**: `worker/src/worker/git_utils.py` — worker-local, API unchanged
- **Push location**: token injected in `task_service.trigger_push()` before calling `git_service` — `git_service.py` stays token-agnostic
- **Token never logged**: `agent_runner.py` MUST log `github_token_set: bool`, not the token value

## Observability Requirements (Constitution IV)

Worker must emit these structured log events (existing `extra={}` pattern):

```python
# Before clone
logger.info("clone_started", extra={"event": "clone_started", "job_id": ..., "git_url": ..., "branch": ..., "token_set": bool(github_token)})

# On success
logger.info("clone_succeeded", extra={"event": "clone_succeeded", "job_id": ..., "branch_checked_out": ...})

# On failure
logger.error("clone_failed", extra={"event": "clone_failed", "job_id": ..., "error": ..., "git_url": ...})
# NOTE: git_url must be sanitized — strip token if embedded
```
