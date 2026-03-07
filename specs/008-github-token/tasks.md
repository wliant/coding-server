# Tasks: GitHub Token Integration

**Input**: Design documents from `/specs/008-github-token/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included — Constitution Principle II (TDD) is NON-NEGOTIABLE; tests are written before implementation in every story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: API contract and dependency changes that all stories depend on

- [ ] T001 Update `openapi.json` — add optional `branch` field to `CreateTaskRequest` and `TaskDetailResponse` schemas; add `github.token` description to `PUT /settings`; bump `info.version` to `0.5.0` per `specs/008-github-token/contracts/openapi-changes.md`
- [ ] T002 Regenerate TypeScript client by running `cd web && npm run generate` (depends on T001)
- [ ] T003 [P] Add `"gitpython>=3.1"` to dependencies list in `worker/pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database and ORM changes that User Stories 2 and 3 depend on

**⚠️ CRITICAL**: No user story 2 or 3 work can begin until this phase is complete

- [ ] T004 Write Alembic migration `api/alembic/versions/0008_add_branch_to_jobs.py` — `op.add_column("jobs", sa.Column("branch", sa.String(255), nullable=True))` with matching downgrade; revision `"0008"`, down_revision `"0007"`
- [ ] T005 [P] Add `branch: Mapped[str | None] = mapped_column(String(255), nullable=True)` to `Job` class in `api/src/api/models/job.py`
- [ ] T006 [P] Add `branch: Mapped[str | None] = mapped_column(String(255), nullable=True)` to `Job` class in `worker/src/worker/models.py`

**Checkpoint**: Migration and ORM models updated — stories 2 and 3 can now begin

---

## Phase 3: User Story 1 — Configure GitHub Token in Settings (Priority: P1) 🎯 MVP

**Goal**: Users can save, update, and view (masked) a GitHub Personal Access Token in a new dedicated GitHub tab in Settings. Token is stored and returned via the existing settings API.

**Independent Test**: Open `http://localhost:3000/settings`, navigate to the GitHub tab, enter a token, save, refresh — the field shows a masked value. Confirmed by: `GET /settings` returns `{"settings": {"github.token": "<value>", ...}}`.

### Tests for User Story 1

> **Write these tests FIRST — confirm they FAIL before implementation (T008)**

- [ ] T007 [P] [US1] Write pytest tests in `api/tests/test_setting_service.py` (or existing settings test file) covering: `GET /settings` returns `github.token` with empty-string default; `PUT /settings` accepts and persists `github.token`; unknown key still returns 422

### Implementation for User Story 1

- [ ] T008 [P] [US1] Add `"github.token"` to `ALLOWED_KEYS` set and `DEFAULTS` dict (default `""`) in `api/src/api/services/setting_service.py` — make T007 tests pass
- [ ] T009 [P] [US1] Create `web/src/components/settings/GitHubSettings.tsx` — component with Props `{ initialSettings: Record<string, string>; onSave: (settings: Record<string, string>) => Promise<void> }`; password-type input for token; shows masked placeholder `••••••••` when token is set; only sends update when field is explicitly changed; Save / Cancel buttons with success/error feedback (follow `AgentSettings.tsx` pattern)
- [ ] T010 [US1] Add **GitHub** tab to `web/src/app/settings/page.tsx` as a third tab alongside General and Agent Settings; render `<GitHubSettings initialSettings={settings} onSave={handleSave} />` (depends on T009)

**Checkpoint**: User Story 1 fully functional — token can be saved and is masked in UI independently of stories 2 and 3

---

## Phase 4: User Story 2 — Clone Repository Before Agent Starts (Priority: P2)

**Goal**: When a task is submitted for a project with a `git_url`, the worker clones the repository (with optional branch selection) into the task's working directory before the coding agent runs. Clone failures transition the task to `failed`.

**Independent Test**: Submit a task for a project with a public GitHub `git_url` and a branch name. Observe `clone_started` / `clone_succeeded` log events. Inspect the work directory — it contains the cloned repository on the correct branch. Submit with a non-existent branch — directory has the default branch content with the new branch checked out.

### Tests for User Story 2

> **Write these tests FIRST — confirm they FAIL before implementation (T014, T016)**

- [ ] T011 [P] [US2] Write pytest unit tests in `worker/tests/test_git_utils.py` covering: `inject_github_token()` transforms HTTPS GitHub URLs and leaves SSH/non-GitHub URLs unchanged; `clone_repository()` with existing branch checks out correct branch; `clone_repository()` with non-existent branch creates branch from default; `clone_repository()` raises on network failure; token is NOT present in any raised exception message (use tmp dir for file system tests)
- [ ] T012 [P] [US2] Write pytest unit tests in `worker/tests/test_agent_runner.py` (or existing agent_runner test file) covering: `run_coding_agent()` calls `clone_repository()` when `project.git_url` is set; emits `clone_started` structured log; returns `(False, error_msg)` and does NOT call `CodingAgent` when clone raises; does NOT call `clone_repository()` when `project.git_url` is None

### Implementation for User Story 2

- [ ] T013 [US2] Add `branch: str | None = None` to `CreateTaskRequest` schema and `TaskDetailResponse` schema in `api/src/api/schemas/task.py`; update `task_service.create_task()` in `api/src/api/services/task_service.py` to pass `branch=req.branch` when constructing the `Job` object
- [ ] T014 [US2] Create `worker/src/worker/git_utils.py` implementing `inject_github_token(url, token) -> str` and `clone_repository(git_url, to_path, branch=None, github_token="") -> None` per `specs/008-github-token/data-model.md`; two-phase branch strategy (try clone with branch → on `GitCommandError` clone default then `create_head(branch).checkout()`); make T011 tests pass
- [ ] T015 [US2] Update `worker/src/worker/agent_runner.py` — after creating the `WorkDirectory` DB record and before calling `CodingAgent`: fetch `github_token = agent_settings.get("github.token", "")`, call `await asyncio.to_thread(clone_repository, project.git_url, work_dir, branch=job.branch, github_token=github_token)` when `project.git_url` is set; emit `clone_started` (with `token_set: bool`), `clone_succeeded`, `clone_failed` structured log events; on clone failure return `(False, f"clone failed: {exc}")`; make T012 tests pass

**Checkpoint**: User Story 2 fully functional — tasks for projects with `git_url` start with cloned repository content

---

## Phase 5: User Story 3 — Push Work to GitHub Using Token (Priority: P3)

**Goal**: When pushing a completed task's work to a GitHub HTTPS URL, the system injects the configured `github.token` into the URL for authentication — no system-level git credentials required.

**Independent Test**: Complete a task for a private GitHub project with a configured token. Click "Push to Remote". The branch `task/{id[:8]}` appears on GitHub without any SSH or credential-helper configuration.

### Tests for User Story 3

> **Write these tests FIRST — confirm they FAIL before implementation (T017)**

- [ ] T016 [US3] Write pytest tests in `api/tests/test_task_service.py` (or existing task service test) for `trigger_push()`: when `github.token` is set in settings and project `git_url` is a GitHub HTTPS URL, `git_service.push_working_directory_to_remote` is called with a token-injected URL; when token is empty, URL is passed unchanged; when `git_url` is an SSH URL (`git@github.com:...`), URL is passed unchanged

### Implementation for User Story 3

- [ ] T017 [US3] Add `_inject_github_token(url: str, token: str) -> str` private helper to `api/src/api/services/task_service.py`; update `trigger_push()` to call `await setting_service.get_settings(db)`, extract `github.token`, and pass `_inject_github_token(project.git_url, token)` as the `remote_url` argument to `git_service.push_working_directory_to_remote()`; make T016 tests pass

**Checkpoint**: All three user stories are independently functional and the full clone → agent → push round-trip works with a GitHub token

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Observability hardening and end-to-end validation

- [ ] T018 [P] Audit `worker/src/worker/git_utils.py` and `worker/src/worker/agent_runner.py` — ensure the token-embedded URL is never passed to logger calls; sanitize by stripping credentials from URL before any log message (e.g., `re.sub(r'https://[^@]+@', 'https://', url)`)
- [ ] T019 [P] Verify `web/src/app/settings/page.tsx` and `web/src/components/settings/GitHubSettings.tsx` pass TypeScript strict-mode check: `cd web && npx tsc --noEmit`
- [ ] T020 Run full end-to-end verification per `specs/008-github-token/quickstart.md` — configure token, submit task with git_url + branch, verify clone, verify push to private repo

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Requires T001–T003 — BLOCKS User Stories 2 and 3 (model/migration changes)
- **User Story 1 (Phase 3)**: Requires T001/T002 only — can start in parallel with Foundational
- **User Story 2 (Phase 4)**: Requires T004–T006 (Foundational) + T001/T002 (OpenAPI)
- **User Story 3 (Phase 5)**: Requires T001/T002; does NOT require US2 to complete
- **Polish (Phase 6)**: Requires all desired stories to be complete

### User Story Dependencies

- **US1**: Depends on T001/T002 only (settings schema unchanged — no dependency on Foundational)
- **US2**: Depends on Foundational (T004–T006) + T001/T002
- **US3**: Depends on T001/T002 only (no schema or migration changes beyond what's already in openapi.json)

### Within Each User Story

- Tests MUST be written and confirmed FAILING before implementation tasks
- Models/schemas before services
- Services before integration with agent runner or UI

### Parallel Opportunities

- T003 (gitpython dep) runs in parallel with T001/T002
- T004/T005/T006 (Foundational) can all run in parallel with each other once T001 is done
- T007/T008/T009 (US1) can all run in parallel
- T011/T012 (US2 tests) can run in parallel; T013 runs in parallel with them
- T014 (git_utils impl) MUST wait for T011 to confirm tests fail
- T015 (agent_runner update) MUST wait for T012 to confirm tests fail AND T014 to pass

---

## Parallel Example: User Story 2

```
# All three can launch in parallel:
T011: Write worker/tests/test_git_utils.py (confirm FAIL)
T012: Write worker/tests/test_agent_runner.py (confirm FAIL)
T013: Update api/src/api/schemas/task.py + task_service.create_task()

# Then in parallel (once T011 FAIL confirmed):
T014: Create worker/src/worker/git_utils.py (makes T011 pass)

# Sequential after T014 passes and T012 FAIL confirmed:
T015: Update worker/src/worker/agent_runner.py (makes T012 pass)
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1: T001 → T002 (+ T003 in parallel)
2. Complete US1: T007 → T008 → T009 → T010
3. **STOP and VALIDATE**: GitHub token visible in Settings UI, stored and retrievable
4. Ship MVP — token management works independently of clone/push

### Incremental Delivery

1. Phase 1 + US1 → GitHub token in Settings ✅
2. Phase 2 + US2 → Repositories auto-cloned before agent runs ✅
3. US3 → Push uses token for private repos ✅
4. Phase 6 Polish → Full observability and security hardening ✅

---

## Notes

- [P] tasks = different files, no blocking dependencies within the phase
- TDD is required by Constitution Principle II — never implement before the test exists and fails
- Token MUST NOT appear in any log output — sanitize URLs in log calls (T018)
- `git_service.py` in the API is NOT modified — token is always injected by the caller before the URL is passed in
- Worker's `clone_repository()` is synchronous (GitPython is sync) — wrap with `asyncio.to_thread()` in `agent_runner.py`
