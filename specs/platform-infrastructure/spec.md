# Platform Infrastructure
Last updated: 2026-03-13

## Overview

Cross-cutting concerns that support the entire system: project management, agent registry, application settings, the sandbox execution environment, MCP tool servers, database migrations, Docker Compose deployment, and the web UI shell.

## Domain Concepts

### Projects

Projects represent codebases that tasks operate on. They can be "new" (scaffolded from scratch) or "existing" (cloned from a git URL).

- Auto-created when a task is submitted for a new project
- `source_type`: `"new"` or `"existing"`
- `git_url`: nullable; set for existing projects, optional for new
- `name`: nullable; display name for the project

### Agent Registry

Database-backed table of available coding agents. New agents can be added by inserting rows — no code deploy required. The task submission form's Agent dropdown is populated from `GET /agents` (active agents only).

**Seeded agents** (4 total):

| Identifier | Display Name | Port |
|-----------|-------------|------|
| `simple_crewai_pair_agent` | Spec-Driven Development Agent | 8001 |
| `crewai_coding_team` | CrewAI Coding Team | — (stub) |
| `simple_langchain_deepagent` | LangChain Deep Research Agent | 8004 |
| `openhands_agent` | OpenHands Agent | 8005 |

### Settings

Key-value configuration store with namespaced keys. All settings have built-in defaults for fresh deployments. Changes take effect on the next operation without service restart.

**Known keys:**

| Key | Default | Description |
|-----|---------|-------------|
| `agent.work.path` | `/agent-work` | Base directory for agent work (legacy, unused by new workers) |
| `agent.simple_crewai.llm_provider` | `ollama` | LLM provider: ollama, openai, anthropic |
| `agent.simple_crewai.llm_model` | `qwen2.5-coder:7b` | Model name |
| `agent.simple_crewai.llm_temperature` | `0.2` | Temperature (0.0-2.0) |
| `agent.simple_crewai.ollama_base_url` | `http://localhost:11434` | Ollama endpoint |
| `agent.simple_crewai.openai_api_key` | (empty) | OpenAI API key |
| `agent.simple_crewai.anthropic_api_key` | (empty) | Anthropic API key |
| `github.token` | (empty) | GitHub Personal Access Token |

API key fields display `••••••••` when a value is stored.

### Sandbox Service (port 8006)

A general-purpose Python execution environment providing workspace APIs. Sandboxes are independent of agent workers — they provide file CRUD, command execution (sync + streaming), and zip download capabilities.

**Workspace API:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /health` | GET | Health check |
| `GET /files` | GET | List files recursively (query param: `path`) |
| `GET /files/{path:path}` | GET | Read file content |
| `PUT /files/{path:path}` | PUT | Write file (`{content}`) |
| `DELETE /files/{path:path}` | DELETE | Delete file or directory |
| `POST /mkdir/{path:path}` | POST | Create directory (recursive) |
| `GET /download` | GET | Download workspace as zip archive |
| `POST /execute` | POST | Synchronous command execution → `{exit_code, stdout, stderr}` |
| `POST /execute/stream` | POST | SSE streaming of command output |

**Key properties:**
- Containerized: `python:3.12-slim` + `git`, `curl`, `jq`, `build-essential`
- Non-root user (`appuser`) with ownership of `/workspace`
- Path traversal protection: resolved paths must stay within workspace (403 otherwise)
- Binary file reads return 400
- File content reads truncate at 500 KB with warning
- Command timeout: 300s default (configurable)
- SSE events: `stdout`, `stderr`, `exit`, `error`

**Registration:** Sandboxes register with the controller and send heartbeats (same pattern as workers). Labels (e.g., `["python", "git"]`) describe available capabilities. Controller persists sandbox records to the `sandboxes` DB table and tracks liveness in-memory.

### MCP Tools Gateway (port 8002)

FastMCP gateway mounting three namespace servers:

| Namespace | Tools |
|-----------|-------|
| `filesystem` | read_file, write_file, list_directory, create_directory |
| `git` | git_clone, git_commit, git_push, git_status, git_diff |
| `shell` | run_command (sandboxed) |

Single Docker service exposed on port 8002 via streamable HTTP transport. Currently in stub/minimal implementation status.

## Data Model

### `projects` table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | |
| name | VARCHAR(255) | nullable | Display name |
| source_type | VARCHAR(20) | NOT NULL | "new" or "existing" |
| git_url | TEXT | nullable | Remote repository URL |
| status | VARCHAR(20) | NOT NULL, default "active" | |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() | |

### `agents` table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | |
| identifier | VARCHAR(100) | NOT NULL, UNIQUE | Internal library identifier |
| display_name | VARCHAR(200) | NOT NULL | User-facing name |
| is_active | BOOLEAN | NOT NULL, default true | Shown in agent selector when true |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | |

### `settings` table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| key | VARCHAR(100) | PK | Namespaced setting key |
| value | TEXT | NOT NULL | Setting value as string |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() | |

### `sandboxes` table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | |
| sandbox_id | VARCHAR(255) | NOT NULL, UNIQUE | Proposed by sandbox on registration |
| sandbox_url | VARCHAR(255) | NOT NULL | Externally-reachable URL |
| ip_address | VARCHAR(45) | nullable | IPv4/IPv6 address |
| status | VARCHAR(20) | NOT NULL, default "free" | free, allocated, unavailable, unreachable |
| labels | TEXT[] | nullable | Capability tags |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() | |
| last_heartbeat_at | TIMESTAMPTZ | NOT NULL, default now() | |

## API Contracts

### Main API Endpoints (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/agents` | List active agents |
| GET | `/projects` | List named projects |
| GET | `/settings` | Get all settings |
| PUT | `/settings` | Update settings (batch key-value) |
| GET | `/workers` | Proxy to controller |
| GET | `/sandboxes` | Proxy to controller |

### Database Migrations

Alembic migrations in `api/alembic/versions/`, sequential numbering:

| Migration | Description |
|-----------|-------------|
| 0001 | Initial schema (projects, jobs, work_directories) |
| 0002 | Task fields + settings table |
| 0003 | Make project name nullable |
| 0004 | Add lease_holder + lease_expires_at to jobs |
| 0005 | Add agents table |
| 0006 | Add agent_id FK to jobs |
| 0007 | Update agent seeds |
| 0008 | Add branch column to jobs |
| 0009 | Drop deprecated dev_agent_type/test_agent_type columns |
| 0010 | Add assigned_worker_id + assigned_worker_url to jobs |
| 0011 | Add task_type + commits_to_review to jobs |
| 0012 | Add openhands_agent to agents seed data |
| 0013 | Add sandboxes table |

## Service Architecture

### Docker Compose

**Services** (11 total):

| Service | Port | Description |
|---------|------|-------------|
| `postgres` | 5432 | PostgreSQL 16 database |
| `redis` | 6379 | Redis cache/queue |
| `migrate` | — | Runs Alembic migrations, then exits |
| `api` | 8000 | FastAPI REST backend |
| `controller` | 8003 | Agent controller/orchestrator |
| `tools` | 8002 | FastMCP tool gateway |
| `simple_crewai_pair_agent` | 8001 | CrewAI worker |
| `simple_langchain_deepagent` | 8004 | LangChain worker |
| `openhands_agent` | 8005 | OpenHands worker |
| `sandbox` | 8006 | Sandbox execution environment |
| `web` | 3000 | Next.js web frontend |

**Compose files** (4 profiles):

| File | Purpose | Data Persistence |
|------|---------|-----------------|
| `compose.yaml` | Base service definitions | — |
| `compose.dev.yaml` | Dev: hot-reload, host ports, bind mounts | Host dirs (`./data/postgres`, `./agent-work`) |
| `compose.e2e.yaml` | E2E tests: isolated, offset ports | Anonymous volumes (ephemeral) |
| `compose.prod.yaml` | Production: resource limits | Named Docker volumes |

**Startup order**: `postgres` → `migrate` → `api` + `redis` → `controller` → workers + sandbox + tools → `web`

### Health Checks

Every service exposes a `/health` endpoint. Docker healthcheck configured on all services for dependency ordering.

## UI Components

### Navigation (Sidebar)

Links: Tasks, Workers, Sandboxes, Settings

### Settings Page (`web/src/app/settings/`)

Three tabs:

**Agent Settings Tab:**
- Section for `simple_crewai_pair_agent`:
  - LLM Provider (select: ollama, openai, anthropic)
  - Model Name (text)
  - Temperature (numeric, 0.0-2.0)
  - Ollama Base URL (text)
  - OpenAI API Key (masked)
  - Anthropic API Key (masked)

**GitHub Tab:**
- GitHub Personal Access Token (masked)

**Appearance Tab:**
- Theme selection (light/dark mode)

All settings persisted via explicit Save action.

### Web UI Shell

- **Framework**: Next.js 15 App Router + React 19
- **Styling**: Tailwind CSS + shadcn/ui components
- **API Client**: Generated TypeScript client via `@hey-api/openapi-ts` (in `web/src/client/`, do not hand-edit)
- **Theme**: Light/dark mode support

## Configuration

| Variable | Service | Description |
|----------|---------|-------------|
| `DATABASE_URL` | api, controller, workers | PostgreSQL connection string |
| `REDIS_URL` | api | Redis connection string |
| `NODE_ENV` | web | Node.js environment |
| `NEXT_PUBLIC_API_URL` | web | API URL for server-side calls |
| `NEXT_PUBLIC_WORKER_URL` | web | Fallback worker URL (dev) |

## Cross-Context Dependencies

- **Task Lifecycle**: Projects and agents are referenced by tasks; settings provide LLM config
- **Orchestration**: Controller reads agents table; sandbox registry persisted to sandboxes table
- **Agent Execution**: Workers depend on tools gateway; settings provide agent configuration
- **Git Integration**: Settings store GitHub token
