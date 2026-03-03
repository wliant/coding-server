# Implementation Plan: Cross-Platform Build Tool

**Branch**: `003-cross-platform-build` | **Date**: 2026-03-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-cross-platform-build/spec.md`

## Summary

Replace the project's `Makefile` with a `Taskfile.yml` using [Taskfile (go-task) v3](https://taskfile.dev) — a cross-platform, single-binary task runner that requires no Unix tooling on Windows. All 15 existing Makefile targets are migrated 1:1. The task runner wraps existing `docker compose` commands; Taskfile's embedded `mvdan/sh` interpreter provides POSIX shell compatibility on all platforms without bash. The `Makefile` is deleted upon completion, and a GitHub Actions CI workflow is established.

---

## Technical Context

**Language/Version**: YAML (Taskfile.yml) — no host programming language required
**Primary Dependencies**: Taskfile (go-task) v3.48.0 — single binary, no transitive dependencies
**Storage**: N/A
**Testing**: Functional verification — run each `task <name>` and confirm behavior matches current `make <name>` output
**Target Platform**: Windows (via `winget`), macOS (via Homebrew), Linux (via install script) — all host OS
**Project Type**: Developer tooling / build system migration
**Performance Goals**: N/A — task runner is a thin orchestration wrapper
**Constraints**: No bash, WSL, or Unix tools required on host; all bash-dependent scripts run inside Docker containers; Python 3 + Node.js required on host for `generate`, `test-web`, `lint-api`, `check-openapi` (unchanged from existing Makefile prerequisites)
**Scale/Scope**: 15 tasks, 1 `Taskfile.yml`, 1 GitHub Actions workflow file, README and CLAUDE.md updates

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity-First | ✅ Pass | Single `Taskfile.yml` at repo root — no new abstractions, no new packages, 1:1 target mapping |
| II. Test-Driven Development | ✅ Pass | Each task has defined acceptance scenarios (spec). Functional verification tests are the "tests": run each task and confirm output matches expected behavior. CI run serves as automated gate. |
| III. Modularity & Single Responsibility | ✅ Pass | Each task has one clearly stated purpose matching the original Makefile target description |
| IV. Observability | ✅ Pass | All tasks output to stdout; `task --list` surfaces descriptions; Docker Compose provides service logging unchanged |
| V. Incremental & Independent Delivery | ✅ Pass | 4 user stories are independently implementable. P1 (Windows) and P2 (macOS) can be verified on their respective platforms independently |
| VI. API-First with OpenAPI | ✅ N/A | No REST API is introduced or modified. Explicit exception: this is a developer tooling migration. The `generate` and `check-openapi` tasks support the existing OpenAPI workflow unchanged. |

**Complexity Tracking**: No violations. No complexity justification required.

---

## Project Structure

### Documentation (this feature)

```text
specs/003-cross-platform-build/
├── plan.md              # This file
├── research.md          # Phase 0 output ✅
├── data-model.md        # Phase 1 output — N/A (no data entities)
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
/ (repo root)
├── Taskfile.yml            ← NEW: replaces Makefile
├── Makefile                ← DELETED: removed as final step (FR-009)
├── CLAUDE.md               ← UPDATED: all make <target> → task <target>
└── .github/
    └── workflows/
        └── ci.yml          ← NEW: GitHub Actions CI using go-task/setup-task@v1
```

**Structure Decision**: Root-level only. No new source directories, packages, or modules. `Taskfile.yml` lives at the repo root alongside `compose.yaml`, consistent with Go project conventions and Taskfile's own convention.

---

## Phase 0: Research Findings

See [research.md](./research.md) for full details. Key decisions:

1. **Tool**: Taskfile v3 — embedded `mvdan/sh` provides POSIX compatibility on Windows without bash
2. **e2e exit code**: Use `defer:` — replaces manual `EXIT=$?` shell capture cleanly
3. **`check-openapi` adaptation**: Inline as Python commands; eliminate `bash` script dependency (see below)
4. **`generate`**: Remains on host — Python 3 + Node.js required (unchanged from Makefile)
5. **CI**: GitHub Actions with `go-task/setup-task@v1`

---

## Phase 1: Design

### Task Mapping

All 15 Makefile targets map directly to Taskfile tasks. No tasks added or removed.

| Makefile target | Taskfile equivalent | Notes |
|-----------------|--------------------|----|
| `help` | `task --list` (built-in) | Taskfile renders `desc:` fields automatically |
| `dev` | `task dev` | Direct `docker compose` wrapper |
| `dev-down` | `task dev-down` | Direct `docker compose` wrapper |
| `e2e` | `task e2e` | Uses `defer:` for teardown + exit code (see design below) |
| `prod` | `task prod` | Direct `docker compose` wrapper |
| `prod-down` | `task prod-down` | Direct `docker compose` wrapper |
| `generate` | `task generate` | Runs on host: Python 3 + npm (unchanged) |
| `test-api` | `task test-api` | `docker compose exec` into running api container |
| `test-worker` | `task test-worker` | `docker compose exec` into running worker container |
| `test-tools` | `task test-tools` | `docker compose exec` into running tools container |
| `test-web` | `task test-web` | Runs on host: `npx jest` (unchanged) |
| `test-all` | `task test-all` | Uses `deps:` to call test-api, test-worker, test-tools, test-web |
| `lint-api` | `task lint-api` | Runs on host: `npx @redocly/cli` (unchanged) |
| `logs` | `task logs` | `docker compose logs -f` |
| `shell-api` | `task shell-api` | `docker compose exec api bash` |
| `check-openapi` | `task check-openapi` | **Adapted**: inline Python replaces bash script (see below) |

---

### Key Design Details

#### `e2e` task — `defer:` pattern

The Makefile's shell-based exit code capture is replaced by Taskfile's `defer:`:

```yaml
e2e:
  desc: Run end-to-end tests in isolated environment (separate ports)
  dotenv: ['.env.e2e']
  cmds:
    - defer: docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e down -v
    - docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e up -d --wait
    - docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e run --rm --no-deps test-runner
```

Taskfile propagates the `test-runner` exit code automatically; `defer:` ensures `down -v` always runs.

---

#### `check-openapi` task — Python inline

The `bash api/scripts/check_openapi_fresh.sh` call is replaced by two Python commands to eliminate the bash binary dependency:

```yaml
check-openapi:
  desc: Check if openapi.json is up to date with current FastAPI routes
  vars:
    TMP: '{{.TASKFILE_DIR}}/.task/openapi_check.json'
  cmds:
    - PYTHONPATH=api/src python3 api/scripts/export_openapi.py --output {{.TMP}}
    - |
      python3 -c "
      import json, sys
      a = json.load(open('openapi.json'))
      b = json.load(open('{{.TMP}}'))
      if a != b:
          print('openapi.json is STALE — run: task generate')
          sys.exit(1)
      print('openapi.json is up to date')"
```

This is cross-platform: `mvdan/sh` handles env var prefix, Python 3 is already required for `generate`.

**Note**: `export_openapi.py` must accept `--output <path>` argument. The existing script accepts it (confirmed in research). If not, a one-line addition to the script is required as part of the implementation task.

---

#### `test-all` task — `deps:` for parallel/sequential execution

```yaml
test-all:
  desc: Run all pytest suites and web jest suite
  deps: [test-api, test-worker, test-tools, test-web]
```

Taskfile runs `deps:` tasks concurrently by default. Since `test-web` is independent (host-side) and the container tests are independent, concurrent execution is acceptable and faster than the sequential Makefile version.

---

#### `dotenv:` strategy

```yaml
version: '3'
dotenv: ['.env']    # global default — loaded by all tasks

tasks:
  e2e:
    dotenv: ['.env.e2e']   # override for e2e: load .env.e2e instead
    ...
```

---

#### GitHub Actions CI workflow

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: go-task/setup-task@v1
        with:
          version: '3.x'
      - name: Start dev environment
        run: task dev
      - name: Wait for services
        run: docker compose -f compose.yaml -f compose.dev.yaml wait api worker tools
      - name: Run tests
        run: task test-all
```

---

### `Taskfile.yml` Full Structure

```yaml
version: '3'

dotenv: ['.env']

tasks:

  dev:
    desc: Start local development environment with hot-reload
    cmds:
      - docker compose -f compose.yaml -f compose.dev.yaml --env-file .env up

  dev-down:
    desc: Stop local development environment
    cmds:
      - docker compose -f compose.yaml -f compose.dev.yaml down

  e2e:
    desc: Run end-to-end tests in isolated environment (separate ports)
    dotenv: ['.env.e2e']
    cmds:
      - defer: docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e down -v
      - docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e up -d --wait
      - docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e run --rm --no-deps test-runner

  prod:
    desc: Start production environment
    cmds:
      - docker compose -f compose.yaml -f compose.prod.yaml up -d

  prod-down:
    desc: Stop production environment (WARNING — do NOT add -v, it destroys volumes)
    cmds:
      - docker compose -f compose.yaml -f compose.prod.yaml down

  generate:
    desc: Export OpenAPI spec and regenerate TypeScript client
    cmds:
      - PYTHONPATH=api/src python3 api/scripts/export_openapi.py
      - cd web && npm run generate

  test-api:
    desc: Run api pytest suite (requires dev environment running)
    cmds:
      - docker compose -f compose.yaml -f compose.dev.yaml exec api python -m pytest tests/ -p no:cacheprovider

  test-worker:
    desc: Run worker pytest suite (requires dev environment running)
    cmds:
      - docker compose -f compose.yaml -f compose.dev.yaml exec worker python -m pytest tests/ -p no:cacheprovider

  test-tools:
    desc: Run tools pytest suite (requires dev environment running)
    cmds:
      - docker compose -f compose.yaml -f compose.dev.yaml exec tools python -m pytest tests/ -p no:cacheprovider

  test-web:
    desc: Run web jest suite
    cmds:
      - cd web && npx jest

  test-all:
    desc: Run all pytest suites and web jest suite
    deps: [test-api, test-worker, test-tools, test-web]

  lint-api:
    desc: Lint OpenAPI spec with Redocly
    cmds:
      - npx @redocly/cli lint openapi.json

  logs:
    desc: Tail logs from all dev services
    cmds:
      - docker compose -f compose.yaml -f compose.dev.yaml logs -f

  shell-api:
    desc: Open bash shell in api container
    cmds:
      - docker compose -f compose.yaml -f compose.dev.yaml exec api bash

  check-openapi:
    desc: Check if openapi.json is up to date with current FastAPI routes
    vars:
      TMP: '{{.TASKFILE_DIR}}/.task/openapi_check.json'
    cmds:
      - PYTHONPATH=api/src python3 api/scripts/export_openapi.py --output {{.TMP}}
      - |
        python3 -c "
        import json, sys
        a = json.load(open('openapi.json'))
        b = json.load(open('{{.TMP}}'))
        if a != b:
            print('openapi.json is STALE — run: task generate')
            sys.exit(1)
        print('openapi.json is up to date')"
```

---

## Post-Design Constitution Re-Check

All principles remain satisfied after Phase 1 design:

- **Simplicity**: `Taskfile.yml` is a direct YAML translation of the Makefile. The `check-openapi` adaptation uses Python inline (2 commands) rather than a bash script — simpler, not more complex.
- **TDD**: Each task is verified by running it and comparing output/behavior to the existing Makefile target.
- **Modularity**: No coupling between tasks except `test-all → deps`.
- **Observability**: Task output goes to stdout; `task --list` surfaces all tasks.
- **API-First**: No API changes. `generate` and `check-openapi` preserve the existing OpenAPI workflow.

---

## Delivery Order (by user story priority)

| Story | Scope | Delivers |
|-------|-------|---------|
| **P1** — Windows native | `Taskfile.yml` (all docker-compose tasks), README install section, Makefile deleted | SC-001, SC-002, SC-005 |
| **P2** — macOS parity | macOS install validation, `generate` + `check-openapi` tasks, CLAUDE.md updated | SC-002, SC-003, SC-005 |
| **P3a** — Discoverability | All task `desc:` fields, `task --list` verified, auto-completion docs | SC-003 |
| **P3b** — CI/CD | `.github/workflows/ci.yml` with `go-task/setup-task@v1` | SC-004 |
