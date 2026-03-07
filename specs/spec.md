# Coding Machine — System Specification

**Version**: 1.0.0
**Last Updated**: 2026-03-07

## 1. System Overview

Coding Machine is a multi-service AI software development system that accepts natural-language coding tasks from a single user, executes them via LLM-powered agents, and pushes the resulting code to Git repositories.

### Architecture

Four service components orchestrated via Docker Compose:

| Service | Technology | Port | Role |
|---------|-----------|------|------|
| **web** | Next.js 15 / React 19 / TypeScript | 3000 | Browser-based UI |
| **api** | FastAPI 0.115+ / SQLAlchemy 2 / asyncpg | 8000 | REST API backend |
| **worker** | Python 3.12 / CrewAI | 8001 | Background job processor |
| **tools** | FastMCP gateway | 8002 | MCP tool servers (filesystem, git, shell) |

Supporting infrastructure:
- **PostgreSQL 16** — primary persistent store
- **Redis** — job queue and inter-service state sharing
- **Alembic** — database migrations

### Build System

Cross-platform task runner via [Taskfile](https://taskfile.dev) (`Taskfile.yml`). All commands use `task <target>` and work natively on Windows, macOS, and Linux. Docker Compose wraps all service management — no host-level shell scripts required.

### API-First Development

- FastAPI auto-generates the OpenAPI 3.1 spec
- `openapi.json` is committed to the repo root as the source of truth
- TypeScript client is generated via `@hey-api/openapi-ts` into `web/src/client/`
- Spec validated in CI with `@redocly/cli lint`

---

## 2. Data Model

### Tables

#### `projects`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | |
| name | VARCHAR(255) | nullable | Display name; nullable for auto-created projects |
| source_type | VARCHAR(20) | NOT NULL | "new" or "existing" |
| git_url | TEXT | nullable | Remote repository URL |
| status | VARCHAR(20) | NOT NULL, default "active" | |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() | |

#### `jobs`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | |
| project_id | UUID | FK → projects.id, NOT NULL | |
| requirement | TEXT | NOT NULL | Natural-language task description |
| status | VARCHAR(20) | NOT NULL, default "pending" | pending / in_progress / completed / failed / aborted |
| agent_id | UUID | FK → agents.id, nullable | Selected agent from registry |
| branch | VARCHAR(255) | nullable | Git branch to clone/checkout |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | |
| started_at | TIMESTAMPTZ | nullable | When worker began execution |
| completed_at | TIMESTAMPTZ | nullable | When execution finished |
| error_message | TEXT | nullable | Human-readable error for failed jobs |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() | |
| lease_holder | VARCHAR(36) | nullable | Worker UUID holding the lease |
| lease_expires_at | TIMESTAMPTZ | nullable | Lease TTL expiry timestamp |

#### `agents`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | |
| identifier | VARCHAR(100) | NOT NULL, UNIQUE | Internal library identifier |
| display_name | VARCHAR(200) | NOT NULL | User-facing name |
| is_active | BOOLEAN | NOT NULL, default true | Shown in agent selector when true |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | |

Seed data: `simple_crewai_pair_agent` ("Spec-Driven Development Agent"), `crewai_coding_team` ("CrewAI Coding Team"), `simple_langchain_deepagent` ("LangChain Deep Research Agent").

#### `settings`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| key | VARCHAR(100) | PK | Namespaced setting key |
| value | TEXT | NOT NULL | Setting value as string |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() | |

Known keys and defaults:

| Key | Default | Description |
|-----|---------|-------------|
| `agent.work.path` | `/agent-work` | Base directory for agent work directories |
| `agent.simple_crewai.llm_provider` | `ollama` | LLM provider: ollama, openai, anthropic |
| `agent.simple_crewai.llm_model` | `qwen2.5-coder:7b` | Model name |
| `agent.simple_crewai.llm_temperature` | `0.2` | Temperature (0.0–2.0) |
| `agent.simple_crewai.ollama_base_url` | `http://localhost:11434` | Ollama endpoint |
| `agent.simple_crewai.openai_api_key` | (empty) | OpenAI API key |
| `agent.simple_crewai.anthropic_api_key` | (empty) | Anthropic API key |
| `github.token` | (empty) | GitHub Personal Access Token |

#### `work_directories`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | |
| job_id | UUID | FK → jobs.id, UNIQUE, NOT NULL | One work directory per job |
| path | TEXT | UNIQUE, NOT NULL | Filesystem path |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | |

---

## 3. Features

### 3.1 Task Submission

Users submit tasks via a web form with the following fields:

- **Project**: "New Project" (creates a new record) or select an existing project
- **Project Name**: Required for new projects; not required to be unique
- **Git URL**: Required for existing projects; optional for new projects
- **Branch**: Optional; specifies which branch to clone/checkout
- **Agent**: Required; single selector populated from the agent registry
- **Requirements**: Required; multi-line natural-language description

On submission, the system creates a `Job` record with `pending` status. The user is redirected to the task list.

### 3.2 Task List

Displays all tasks ordered by creation date (newest first) with columns:
- Project name (derived from project name, git URL slug, or "New Project")
- Agent display name
- Status badge
- Submission date
- Actions: Abort (pending only), Edit (aborted only)

Client-side search filters by requirement text and project name.

### 3.3 Task Abort & Edit

- **Abort**: Available only for `pending` tasks. Requires confirmation. Transitions status to `aborted`.
- **Edit**: Available only for `aborted` tasks. Opens the submission form pre-populated with existing values. On resubmit, status returns to `pending`.

### 3.4 Task Detail Page

Accessible by clicking a task in the list. Shows:
- All statuses: task info, requirements, remote git URL, current status, working directory path
- In Progress: elapsed time since started
- Completed: "Push to Remote" action
- Failed: human-readable error message

### 3.5 Push to Remote

Available on completed tasks. Creates a branch named `task/{job_id_prefix}` and force-pushes to the project's git URL. If no git URL is stored, the user can enter one on the detail page before pushing. Uses the configured GitHub token for authentication when pushing to GitHub URLs.

### 3.6 Settings

Three tabs in the Settings page:

**General Tab**:
- Agent Working Directory (`agent.work.path`): file system path for agent work

**Agent Settings Tab**:
- Section for `simple_crewai_pair_agent` with fields:
  - LLM Provider (selection: ollama, openai, anthropic)
  - Model Name (free text)
  - Temperature (numeric, 0.0–2.0)
  - Ollama Base URL (text)
  - OpenAI API Key (masked)
  - Anthropic API Key (masked)
- API key fields display `••••••••` when a value is stored
- All settings have built-in defaults for fresh deployments

**GitHub Tab**:
- GitHub Personal Access Token (masked)
- Used for clone and push operations against GitHub URLs

All settings are persisted via explicit Save action. Changes take effect on the next operation without service restart.

### 3.7 Agent Worker

The worker runs a polling loop:

1. **Reap** expired leases (crashed workers)
2. **Poll** for the next `pending` job
3. **Acquire lease** atomically (compare-and-set on status + lease fields)
4. **Fetch settings** from `GET /settings` API endpoint
5. **Clone repository** if the project has a `git_url` (using GitHub token if configured)
   - If a branch is specified and exists remotely, check it out
   - If a branch is specified but doesn't exist, create it from the default branch
6. **Execute agent** (`simple_crewai_pair_agent.CodingAgent`) with:
   - Working directory: `{agent.work.path}/{job_id}`
   - Project name, requirement text
   - LLM config from settings (provider, model, temperature, URLs, API keys)
7. **Update status** to `completed` or `failed`
8. **Release lease**

Lease pattern: Each lease has a TTL. The worker renews the lease periodically while executing. If a lease expires (worker crash), the job automatically returns to `pending`.

Each worker instance processes one job at a time. Multiple instances can run simultaneously; the lease pattern prevents duplicate processing.

If the settings API is unreachable, the job fails immediately with "unable to fetch agent settings".

### 3.8 Coding Agent (`simple_crewai_pair_agent`)

A standalone Python package using CrewAI with two sequential agents:
- **Coder**: Writes code to fulfill the requirement
- **Reviewer**: Reviews the code for correctness and completeness

Entry point: `CodingAgent(config: CodingAgentConfig).run() → CodingAgentResult`

All LLM configuration is passed via the `CodingAgentConfig` object — the agent does not read environment variables for LLM settings.

Supported providers: `ollama`, `openai`, `anthropic`.

### 3.9 Agent Registry

Database-backed table of available agents. New agents can be added by inserting rows — no code deploy required. The task submission form's Agent field is populated from `GET /agents` (active agents only).

### 3.10 MCP Tool Servers

FastMCP gateway mounts three namespace servers:
- `filesystem`: read_file, write_file, list_directory, create_directory
- `git`: git_clone, git_commit, git_push, git_status, git_diff
- `shell`: run_command (sandboxed)

Single Docker service exposed on port 8002 via streamable HTTP transport.

---

## 4. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/agents` | List active agents |
| GET | `/projects` | List named projects |
| GET | `/tasks` | List all tasks (joined with project + agent) |
| POST | `/tasks` | Create a new task |
| GET | `/tasks/{id}` | Task detail (includes work directory, elapsed time) |
| PATCH | `/tasks/{id}` | Abort or resubmit a task |
| POST | `/tasks/{id}/push` | Push completed task to remote git |
| GET | `/settings` | Get all settings |
| PUT | `/settings` | Update settings |

Full schema: see `openapi.json` at the repository root.

---

## 5. Docker Compose Environments

| File | Purpose | Data Persistence |
|------|---------|-----------------|
| `compose.yaml` | Base service definitions | — |
| `compose.dev.yaml` | Local dev with hot-reload, host port mapping, bind mounts | Host directories (`./data/postgres`, `./agent-work`) |
| `compose.e2e.yaml` | Isolated test environment with offset ports | Anonymous volumes (ephemeral) |
| `compose.prod.yaml` | Production with resource limits, no debug tooling | Named Docker volumes (`postgres_data`, `agent_work`) |

---

## 6. Non-Functional Requirements

- **Single-user application**: No authentication, authorization, or multi-tenant isolation
- **Structured logging**: All services emit structured JSON logs
- **OpenAPI validation**: CI checks that `openapi.json` is in sync with FastAPI routes
- **Test isolation**: Each component's test suite runs independently per component
- **Python**: ruff for linting/formatting; type hints on all public functions; pytest + pytest-asyncio
- **TypeScript**: strict mode; generated client code in `web/src/client/` (do not hand-edit)
- **Cross-platform**: All build commands work on Windows, macOS, and Linux via Taskfile

---

## 7. Assumptions

- Host machine has Docker Desktop installed
- For Ollama provider: Ollama is installed and a compatible model is pulled on the host
- Git credentials (SSH keys or token) are pre-configured in the server environment for push operations
- GitHub token auth applies only to `github.com` URLs; other hosts use system credentials
- No processing timeout — tasks remain in-progress until the agent completes or fails
- Real-time status push (WebSocket) is out of scope; manual refresh is used
- The working directory persists after job completion and is not automatically cleaned up
