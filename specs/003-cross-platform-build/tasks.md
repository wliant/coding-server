# Tasks: Cross-Platform Build Tool

**Input**: Design documents from `/specs/003-cross-platform-build/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths included in every task description

---

## Phase 1: Setup

**Purpose**: Create the Taskfile skeleton and prepare supporting files before writing task definitions.

- [x] T001 Create `Taskfile.yml` at repo root with `version: '3'` header and `dotenv: ['.env']` global config; leave `tasks:` section empty
- [x] T002 [P] Add `.task/` directory entry to `.gitignore` (Taskfile cache directory)
- [x] T003 Read `api/scripts/export_openapi.py` and verify it accepts an `--output <path>` CLI argument; if missing, add `argparse` support: `--output` writes the spec to the given path instead of `openapi.json` (required by `check-openapi` task)

---

## Phase 2: Foundational — Implement All Taskfile Task Definitions

**Purpose**: Write all 15 task definitions into `Taskfile.yml`. This is the core deliverable — all user story verifications depend on this phase being complete.

**⚠️ CRITICAL**: No user story acceptance testing can begin until this phase is complete.

- [x] T004 Implement `dev`, `dev-down`, `prod`, `prod-down` tasks in `Taskfile.yml` — each is a direct `docker compose` wrapper matching the Makefile exactly; `dev`/`dev-down` use `-f compose.yaml -f compose.dev.yaml --env-file .env`; `prod`/`prod-down` use `-f compose.yaml -f compose.prod.yaml`
- [x] T005 Implement `e2e` task in `Taskfile.yml` with `dotenv: ['.env.e2e']` per-task override and `defer:` for guaranteed teardown: first line is `defer: docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e down -v`, then `up -d --wait`, then `run --rm --no-deps test-runner` (see plan.md Phase 1 design)
- [x] T006 Implement `test-api`, `test-worker`, `test-tools` tasks in `Taskfile.yml` — each calls `docker compose -f compose.yaml -f compose.dev.yaml exec <service> python -m pytest tests/ -p no:cacheprovider`; implement `test-web` task calling `cd web && npx jest`
- [x] T007 Implement `test-all` task in `Taskfile.yml` with `deps: [test-api, test-worker, test-tools, test-web]` (concurrent execution via Taskfile deps)
- [x] T008 Implement `logs` and `shell-api` tasks in `Taskfile.yml`; `logs` calls `docker compose -f compose.yaml -f compose.dev.yaml logs -f`; `shell-api` calls `docker compose -f compose.yaml -f compose.dev.yaml exec api bash`
- [x] T009 Implement `lint-api` task in `Taskfile.yml` calling `npx @redocly/cli lint openapi.json`
- [x] T010 Implement `generate` task in `Taskfile.yml`: first command `PYTHONPATH=api/src python3 api/scripts/export_openapi.py`, second command `cd web && npm run generate`
- [x] T011 Implement `check-openapi` task in `Taskfile.yml` using inline Python (no bash dependency): use `vars: TMP: '{{.TASKFILE_DIR}}/.task/openapi_check.json'`; first command exports fresh spec via `PYTHONPATH=api/src python3 api/scripts/export_openapi.py --output {{.TMP}}`; second command runs Python inline to JSON-compare `openapi.json` vs `{{.TMP}}` and exits 1 with "STALE" message if different (see plan.md check-openapi design section)

**Checkpoint**: Run `task --list` — all 15 tasks should appear. Foundation ready.

---

## Phase 3: User Story 1 — Developer on Windows Runs Project Commands (Priority: P1) 🎯 MVP

**Goal**: A developer on Windows with no Unix tooling installs Taskfile via `winget` and runs all project commands natively.

**Independent Test**: On a Windows machine with Docker Desktop and no WSL/GNU Make: install via `winget install Task.Task`, run `task dev` from repo root, confirm Docker Compose dev environment starts. Run `task --list` and confirm all 15 tasks appear with descriptions.

### Implementation for User Story 1

- [x] T012 [US1] Add `desc:` field to every task in `Taskfile.yml` so `task --list` outputs all 15 task names and descriptions (description text must match the Makefile comment text exactly)
- [x] T013 [US1] Functional verification on Windows: run `task dev` → confirm dev environment starts; run `task --list` → confirm 15 tasks shown; run `task test-all` (with dev environment running) → confirm all suites execute; no bash/WSL required at any step

**Checkpoint**: US1 complete — Windows developer can use all 15 tasks via `task <name>` with no Unix tooling.

---

## Phase 4: User Story 2 — Developer on macOS Runs Project Commands (Priority: P2)

**Goal**: A developer on macOS installs Taskfile via Homebrew and runs all project commands using identical `task <name>` syntax.

**Independent Test**: On macOS: `brew install go-task/tap/go-task`, run `task generate` → OpenAPI spec exported to `openapi.json` and TypeScript client regenerated; run `task e2e` → test-runner exit code propagated, teardown always runs.

### Implementation for User Story 2

- [ ] T014 [US2] Functional verification on macOS: run `task generate` → confirm `openapi.json` updated and `web/src/client/` TypeScript files regenerated; run `task e2e` → confirm test-runner exit code (pass or fail) is the exit code of the `task e2e` command and `docker compose down -v` always runs
- [ ] T015 [US2] Functional verification on macOS: run `task check-openapi` after running `task generate` → confirm "up to date" message; manually modify `openapi.json` then run `task check-openapi` → confirm "STALE" message and exit code 1
<!-- T014 and T015 require a macOS machine — deferred to contributor verification -->

**Checkpoint**: US2 complete — macOS developers use identical commands with no behavioral differences from US1.

---

## Phase 5: User Story 3 — Developer Discovers Available Commands (Priority: P3)

**Goal**: A new developer runs `task --list` and `task --summary <name>` to discover all available commands; README provides installation instructions and a make→task migration table.

**Independent Test**: Run `task --list` → 15 tasks listed with one-line descriptions. Run `task --summary e2e` → summary paragraph shown. Read README.md → installation steps for Windows/macOS/Linux visible; migration table visible.

### Implementation for User Story 3

- [x] T016 [US3] Add `summary:` multi-line fields to `e2e`, `test-all`, `generate`, and `check-openapi` tasks in `Taskfile.yml` (these are the most-used tasks; summaries should explain prerequisites and expected output)
- [x] T017 [P] [US3] Create `README.md` at repo root with: (1) Prerequisites section (Docker Desktop, Python 3, Node.js), (2) Install Taskfile section with one-command per platform (Windows: `winget install Task.Task`, macOS: `brew install go-task/tap/go-task`, Linux: install script), (3) Quick Start section (`task dev`), (4) complete make→task migration table (15 rows) matching `quickstart.md` content
- [x] T018 [US3] Add optional "Shell Auto-Completion" section to `README.md` with one-liner completion setup for bash, zsh, fish, and PowerShell (marked as optional/recommended per clarification Q5)

**Checkpoint**: US3 complete — new developer can discover all commands and install the tool from README alone.

---

## Phase 6: User Story 4 — CI/CD Pipeline Uses the New Task Runner (Priority: P3)

**Goal**: A GitHub Actions CI pipeline installs Taskfile, starts the dev environment, and runs `task test-all` on every push and pull request.

**Independent Test**: Push a commit → GitHub Actions workflow triggers → `go-task/setup-task@v1` step passes → `task test-all` step executes all test suites → workflow reports pass/fail.

### Implementation for User Story 4

- [x] T019 [US4] Create `.github/workflows/ci.yml` with: trigger on `push` and `pull_request`, `ubuntu-latest` runner, `actions/checkout@v4`, `go-task/setup-task@v1` with `version: '3.x'`, start dev environment (`task dev`), wait for all services healthy, run `task test-all`
- [x] T020 [P] [US4] Update `CLAUDE.md` Commands section to replace every `make <target>` reference with `task <target>` (dev, test-all, e2e, generate, per-component test commands)

**Checkpoint**: US4 complete — CI pipeline runs `task test-all` and reports results on every push.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and validation — Makefile removal and end-to-end quickstart verification.

- [x] T021 Delete `Makefile` from repo root (FR-009: both files MUST NOT coexist as source of truth once all tasks verified working)
- [x] T022 [P] Run full `quickstart.md` validation: install Taskfile on a clean environment, execute every command in the make→task migration table, confirm each matches expected behavior; update `quickstart.md` with any corrections found

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; T002 and T003 are [P] with T001
- **Foundational (Phase 2)**: Depends on Phase 1 completion — **BLOCKS all user story phases**
- **US1 (Phase 3)**: Depends on Phase 2 completion — no dependencies on other user stories
- **US2 (Phase 4)**: Depends on Phase 2 completion — no dependencies on US1 (same Taskfile.yml, different platform)
- **US3 (Phase 5)**: Depends on Phase 2 completion — T017/T018 in `README.md` are independent of US1/US2 verification tasks
- **US4 (Phase 6)**: Depends on Phase 2 completion — T020 (`CLAUDE.md`) is [P] with T019 (`ci.yml`)
- **Polish (Phase 7)**: T021 (Makefile deletion) depends on all US phases passing; T022 can run in parallel with T021

### User Story Dependencies

- **US1 (P1)**: Start after Phase 2 — no dependency on US2, US3, US4
- **US2 (P2)**: Start after Phase 2 — no dependency on US1, US3, US4
- **US3 (P3)**: Start after Phase 2 — T017/T018 (README) can be written before US1/US2 verification
- **US4 (P3)**: Start after Phase 2 — fully independent of US1/US2/US3

### Within Phase 2 (same file — sequential recommended)

T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 (all in `Taskfile.yml`; write in one pass or sequentially)

---

## Parallel Execution Examples

### Phase 1 — parallel after T001

```text
T001 (Taskfile.yml skeleton) completes first, then in parallel:
  T002: Update .gitignore
  T003: Verify/fix export_openapi.py --output support
```

### Phase 2 — write Taskfile.yml in one pass

```text
Single session recommended (all edits to Taskfile.yml):
  T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011
```

### Phases 3–6 — after Phase 2 checkpoint, all can run in parallel

```text
US1 verification (Windows machine)   ← T012, T013
US2 verification (macOS machine)     ← T014, T015       } concurrent
US3 README + summaries               ← T016, T017, T018 }
US4 CI + CLAUDE.md                   ← T019, T020       }
```

---

## Implementation Strategy

### MVP (User Story 1 Only — Minimum to Unblock Windows Developers)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T011)
3. Complete Phase 3: US1 — add `desc:` fields + Windows verification (T012–T013)
4. **STOP and validate**: All 15 tasks work on Windows with no Unix tooling ✅
5. Windows developers can use `task <name>` immediately

### Incremental Delivery

1. Phase 1 + 2 → Taskfile functional (all platforms, no documentation yet)
2. Phase 3 → **MVP**: Windows support verified ✅
3. Phase 4 → macOS parity confirmed ✅
4. Phase 5 → README + discoverability ✅ (shareable onboarding docs)
5. Phase 6 → CI/CD established ✅
6. Phase 7 → Makefile deleted, cleanup done ✅

### Parallel Team Strategy

With two developers after Phase 2 completes:

- **Developer A**: Phase 3 (US1 Windows verification) + Phase 5 (US3 README)
- **Developer B**: Phase 4 (US2 macOS verification) + Phase 6 (US4 CI)

Both merge before Phase 7 (Makefile deletion).

---

## Notes

- [P] tasks operate on different files and have no logical dependencies on incomplete tasks
- T003 is a prerequisite for T011 (`check-openapi`) — complete it before writing the check-openapi task definition
- T021 (Makefile deletion) is intentionally last — delete only after all 15 `task <name>` equivalents are verified
- `task --list` requires `desc:` fields on tasks (T012) — US1 checkpoint depends on this
- The `e2e` task's `defer:` pattern (T005) is the only non-trivial Taskfile feature in use; refer to `research.md` Decision 3 for the exact syntax
- Commit after each phase checkpoint for clean rollback points
