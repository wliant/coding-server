# coding-machine

A multi-service AI coding assistant built with FastAPI, LangGraph, and Next.js.

## Prerequisites

All platforms require:

- **Docker Desktop** — runs all services (api, worker, tools, web, postgres, redis)

The following are required for code generation and OpenAPI checks:

- **Python 3** — for `task generate` and `task check-openapi`
- **Node.js + npm** — for `task generate`, `task test-web`, `task lint-api`

## Install Taskfile

This project uses [Taskfile](https://taskfile.dev) instead of Make, so all commands work natively on Windows, macOS, and Linux.

**Windows** (PowerShell or Windows Terminal):

```powershell
winget install Task.Task
```

**macOS**:

```bash
brew install go-task/tap/go-task
```

**Linux**:

```bash
sh -c "$(curl -fsSL https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin
```

Verify:

```bash
task --version
```

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start all services with hot-reload
task dev

# 3. View all available commands
task --list
```

## Available Commands

| Command | Description |
|---------|-------------|
| `task dev` | Start local development environment with hot-reload |
| `task dev-down` | Stop local development environment |
| `task e2e` | Run end-to-end tests in isolated environment (separate ports) |
| `task prod` | Start production environment |
| `task prod-down` | Stop production environment |
| `task generate` | Export OpenAPI spec and regenerate TypeScript client |
| `task test-api` | Run api pytest suite (requires dev environment running) |
| `task test-worker` | Run worker pytest suite (requires dev environment running) |
| `task test-tools` | Run tools pytest suite (requires dev environment running) |
| `task test-web` | Run web jest suite |
| `task test-all` | Run all pytest suites and web jest suite |
| `task lint-api` | Lint OpenAPI spec with Redocly |
| `task logs` | Tail logs from all dev services |
| `task shell-api` | Open bash shell in api container |
| `task check-openapi` | Check if openapi.json is up to date with current FastAPI routes |

For detailed help on any command:

```bash
task --summary <command>
# e.g. task --summary e2e
```

## Running Tests

```bash
# Start dev environment first
task dev

# Run all test suites (in another terminal)
task test-all

# Or run individual suites
task test-api
task test-worker
task test-tools
task test-web
```

## Per-Component Tests (inside container)

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec api pytest tests/
docker compose -f compose.yaml -f compose.dev.yaml exec worker pytest tests/
docker compose -f compose.yaml -f compose.dev.yaml exec tools pytest tests/
```

## Type-Check Frontend

```bash
cd web && npx tsc --noEmit
```

## Shell Auto-Completion (Optional)

Taskfile supports shell auto-completion — tab-complete `task <name>` in your shell:

```bash
# bash
task --completion bash >> ~/.bashrc && source ~/.bashrc

# zsh
task --completion zsh >> ~/.zshrc && source ~/.zshrc

# fish
task --completion fish > ~/.config/fish/completions/task.fish

# PowerShell
task --completion powershell >> $PROFILE
```
