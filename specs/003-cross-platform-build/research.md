# Research: Cross-Platform Build Tool

**Feature**: 003-cross-platform-build
**Date**: 2026-03-03

---

## Decision 1: Tool Selection — Taskfile (go-task)

**Decision**: Use [Taskfile (go-task)](https://taskfile.dev) v3 as the Makefile replacement.

**Rationale**:
- Single binary, no runtime dependencies (Go-compiled)
- Uses an embedded POSIX-compatible shell interpreter ([mvdan/sh](https://github.com/mvdan/sh)) on all platforms — **no bash, WSL, or GNU Make required on Windows**
- Since v3.45.3, bundles common POSIX utilities (`cp`, `mv`, `mkdir`, `rm`, etc.) so standard shell idioms work on Windows natively
- YAML-based configuration aligns with the Docker Compose conventions already used in this project
- Native task dependencies, dotenv file support, exit code propagation
- `task --list` and `task --summary <name>` provide built-in discoverability
- Active maintenance: v3.48.0 released January 2026

**Alternatives considered**:
- **Just** (casey/just) — Similar scope but slightly less POSIX-compatible on Windows; no dotenv support built-in
- **npm scripts** — Already available (Node.js present), but limited to JS ecosystem conventions and lacks structured dependency management
- **Turborepo / Nx** — Monorepo orchestration tools, far heavier than needed for a Docker Compose wrapper
- **PowerShell scripts** — Windows-native but would require a separate `.ps1` file per task; not cross-platform without dual maintenance

---

## Decision 2: Cross-Platform Shell Compatibility

**Decision**: Rely on Taskfile's embedded `mvdan/sh` interpreter; no external bash required on any platform.

**Rationale**: Taskfile bundles `mvdan/sh`, a POSIX/bash-compatible Go interpreter. This means:
- POSIX shell syntax (`export`, `if/else`, pipes, env var assignment) works on Windows natively
- `docker compose`, `python3`, `npm`, `npx` are invoked as external processes — they only need to be in `PATH`
- No `bash.exe`, Cygwin, WSL, or Git Bash required on Windows

**Constraint**: Commands that call external bash scripts (`bash api/scripts/...`) still require the `bash` binary. See Decision 4 for how `check-openapi` is handled.

---

## Decision 3: e2e Exit Code Handling

**Decision**: Use Taskfile `defer:` for teardown; rely on Taskfile's native exit code propagation.

**Rationale**: The current Makefile captures the test-runner exit code manually:
```makefile
docker compose ... run --rm test-runner; EXIT=$$?; \
docker compose ... down -v; exit $$EXIT
```

Taskfile's `defer:` runs a command after the task completes, **including on failure**, and the task exit code is automatically the exit code of the failing command. No manual `$?` capture needed:

```yaml
e2e:
  cmds:
    - defer: docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e down -v
    - docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e up -d --wait
    - docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e run --rm --no-deps test-runner
```

This is cleaner, cross-platform, and behaviorally identical to the Makefile version.

---

## Decision 4: `check-openapi` Task Adaptation

**Decision**: Inline the bash script logic using Python directly in the Taskfile task; eliminate the call to `api/scripts/check_openapi_fresh.sh`.

**Problem**: `bash api/scripts/check_openapi_fresh.sh` requires the `bash` binary, which is not available on Windows without Git Bash or WSL.

**Solution**: The script's core logic is: (1) export a fresh OpenAPI spec via Python, (2) compare to `openapi.json`. Both steps can be expressed as cross-platform Taskfile commands using Python and the `export_openapi.py` script (same Python requirement as `generate`):

```yaml
check-openapi:
  vars:
    TMP: '{{.TASKFILE_DIR}}/.task/openapi_check.json'
  cmds:
    - PYTHONPATH=api/src python3 api/scripts/export_openapi.py --output {{.TMP}}
    - python3 -c "
        import json, sys
        a = json.load(open('openapi.json'))
        b = json.load(open('{{.TMP}}'))
        if a != b:
            print('✗ openapi.json is STALE — run: task generate')
            sys.exit(1)
        print('✓ openapi.json is up to date')"
```

**Note**: `export_openapi.py` already accepts `--output` as an argument (confirmed from the existing script). If it does not, a minor script update may be needed. The `.task/` directory is Taskfile's cache directory, safe to use for temp files, and gitignored by default.

**Alternative considered**: Run via `docker compose run --rm` with volume mount — more complex, requires dev environment context, and doesn't align with the "host-level tool for developers" nature of this check.

---

## Decision 5: `generate` Task — Host Execution

**Decision**: Keep `generate` running on the host (Python 3 + Node.js required); no Docker migration for this task.

**Rationale**:
- The `generate` task writes `openapi.json` to the repo root. Running inside Docker would require volume mounts for both the source (api) and target (repo root) with correct write permissions.
- Python 3 and Node.js are expected prerequisites for any developer running `generate` — the current Makefile already assumes this.
- Taskfile's mvdan/sh handles `PYTHONPATH=api/src python3 ...` and `cd web && npm run generate` natively on Windows without bash.

**Host prerequisite**: Python 3 + Node.js must be installed for `generate`, `test-web`, `lint-api`, and `check-openapi`. This is documented in the quickstart.

---

## Decision 6: dotenv File Handling

**Decision**: Use Taskfile's `dotenv:` at the global level for `.env`; per-task `dotenv:` override for `e2e` tasks using `.env.e2e`.

**Key finding**: Taskfile `dotenv:` loads env files before task execution — first file listed takes highest priority.

```yaml
dotenv: ['.env']     # global: loaded for all tasks by default

tasks:
  e2e:
    dotenv: ['.env.e2e']   # overrides global; does NOT merge
    ...
```

Note: The `--env-file` flag is passed explicitly to `docker compose` in the existing Makefile. In Taskfile, we have two layers: (1) dotenv for Taskfile variable interpolation, (2) `--env-file` passed directly to docker compose. Both should be preserved where the Makefile uses them.

---

## Decision 7: CI Platform — GitHub Actions

**Decision**: Create `.github/workflows/ci.yml` using `go-task/setup-task@v1` to install Taskfile in CI.

**Rationale**: No existing CI config. The project is hosted on GitHub (based on git remote context), making GitHub Actions the natural choice. The `go-task/setup-task@v1` action installs Taskfile with one step.

**GitHub Actions snippet**:
```yaml
- uses: go-task/setup-task@v1
  with:
    version: '3.x'
- run: task test-all
```

---

## Decision 8: Installation Commands

| Platform | Recommended command |
|----------|---------------------|
| Windows | `winget install Task.Task` |
| macOS | `brew install go-task/tap/go-task` |
| Linux | `sh -c "$(curl -fsSL https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin` |

All produce the `task` binary. No runtime dependencies beyond the binary itself.

---

## Decision 9: Shell Auto-Completion (Optional)

Taskfile supports shell completion generation:
```bash
task --completion bash >> ~/.bashrc
task --completion zsh >> ~/.zshrc
task --completion fish > ~/.config/fish/completions/task.fish
task --completion powershell >> $PROFILE
```

Documented in README as an optional recommended step per clarification Q5.

---

## Resolved Unknowns

| Unknown | Resolution |
|---------|-----------|
| Windows bash script compatibility | mvdan/sh + Docker containers covers all cases; `check-openapi` inlined as Python |
| e2e exit code propagation | Taskfile `defer:` handles teardown + exit code natively |
| dotenv multi-file handling | Per-task `dotenv:` override for `.env.e2e` tasks |
| CI platform | GitHub Actions with `go-task/setup-task@v1` |
| `generate` host-vs-Docker | Remains on host; Python + Node.js are existing prerequisites |
