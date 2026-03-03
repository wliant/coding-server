# Quickstart: Cross-Platform Build Tool

**Feature**: 003-cross-platform-build

This guide describes the developer experience after migration from Makefile to Taskfile.

---

## Prerequisites

All platforms require:
- **Docker Desktop** (existing requirement — unchanged)

The following are required for specific tasks (`generate`, `test-web`, `lint-api`, `check-openapi`):
- **Python 3** — for `generate` and `check-openapi`
- **Node.js + npm/npx** — for `generate`, `test-web`, `lint-api`

---

## Install Taskfile

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

Verify installation:
```bash
task --version
```

---

## Optional: Shell Auto-Completion

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

---

## Common Workflows

### Start development environment
```bash
task dev
```

### Stop development environment
```bash
task dev-down
```

### Run all tests
```bash
task test-all
```

### Run e2e tests
```bash
task e2e
```

### Regenerate OpenAPI spec + TypeScript client
```bash
task generate
```

### See all available commands
```bash
task --list
```

### Get detailed help for a specific task
```bash
task --summary test-all
```

---

## Migration Reference: make → task

All commands change only the prefix — targets are identical.

| Old command | New command |
|-------------|-------------|
| `make dev` | `task dev` |
| `make dev-down` | `task dev-down` |
| `make e2e` | `task e2e` |
| `make prod` | `task prod` |
| `make prod-down` | `task prod-down` |
| `make generate` | `task generate` |
| `make test-api` | `task test-api` |
| `make test-worker` | `task test-worker` |
| `make test-tools` | `task test-tools` |
| `make test-web` | `task test-web` |
| `make test-all` | `task test-all` |
| `make lint-api` | `task lint-api` |
| `make logs` | `task logs` |
| `make shell-api` | `task shell-api` |
| `make check-openapi` | `task check-openapi` |
| `make help` | `task --list` |
