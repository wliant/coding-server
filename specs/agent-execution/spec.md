# Agent Execution
Last updated: 2026-03-13

## Overview

Worker services receive task delegations from the controller, run LLM-powered coding agents, and report results. Each worker is a self-contained FastAPI service bundled with a specific agent library. Workers register with the controller on startup, execute one task at a time, expose a standard HTTP API, and maintain their own execution state in a local database table.

## Domain Concepts

### Worker State Machine

```
               ┌─────────────────────────┐
               │                         │
    register   ▼    /work POST      ┌────┴────┐
  ──────────► free ───────────────► │in_progress│
               ▲                    └────┬────┘
               │                         │
               │    /free POST      ┌────▼──────────┐
               └────────────────────┤completed/failed│
                                    └───────────────┘
```

- **free**: No active task, eligible to receive work
- **in_progress**: Executing a task (cloning repo, running agent)
- **completed**: Agent finished successfully, holding working directory
- **failed**: Agent encountered an error, holding working directory
- After `/free` is called (by controller during cleanup), worker deletes working directory and returns to `free`

### WorkRequest Payload

The controller sends this payload to `POST /work`:

```json
{
  "task_id": "uuid",
  "requirements": "string",
  "agent_type": "simple_crewai_pair_agent",
  "git_url": "string | null",
  "branch": "string | null",
  "github_token": "string | null",
  "task_type": "build_feature",
  "commits_to_review": null,
  "llm_config": {
    "provider": "ollama",
    "model": "qwen2.5-coder:7b",
    "temperature": 0.2,
    "ollama_base_url": "http://host.docker.internal:11434",
    "openai_api_key": "",
    "anthropic_api_key": ""
  }
}
```

### Agent Runner Flow

1. Receive WorkRequest from controller via `/work`
2. Persist execution start to `worker_executions` table (upsert for retries)
3. Clone repository if `git_url` is provided (with GitHub token injection)
4. Check out specified branch (or create from default if doesn't exist remotely)
5. Execute the agent library with LLM config from settings
6. Update execution status to completed/failed
7. Report status via heartbeat to controller

### Working Directory Lifecycle

- Created at `{WORK_DIR}/{job_id}` when task starts
- Stale directories cleared before clone (handles retried tasks)
- Persists after task completion for file browsing and push operations
- Deleted when controller calls `/free` during cleanup

## Agent Implementations

### 1. CrewAI Pair Agent (`simple_crewai_pair_agent`) — Port 8001

**Location**: `agents/simple_crewai_pair_agent/`

A CrewAI-based agent with two sequential agents:
- **Coder**: Writes code to fulfill the requirement
- **Reviewer**: Reviews the code for correctness and completeness

Entry point: `CodingAgent(config: CodingAgentConfig).run() → CodingAgentResult`

Supported LLM providers: `ollama`, `openai`, `anthropic`. All config passed via `CodingAgentConfig` — no environment variable reads for LLM settings.

### 2. LangChain Deep Agent (`simple_langchain_deepagent`) — Port 8004

**Location**: `agents/simple_langchain_deepagent/`

LangChain-based research agent. Follows the same worker service pattern.

### 3. OpenHands Agent (`openhands_agent`) — Port 8005

**Location**: `agents/openhands_agent/`

Uses OpenHands SDK (`openhands-ai`) with terminal and file-editor tools. Runs a `LocalConversation` in the task's working directory.

Key technical details:
- Tool names: `"terminal"` and `"file_editor"` (must be explicitly imported to register)
- Ollama: requires `native_tool_calling=False` and `base_url` without `/v1` suffix
- Model prefix convention: `ollama/` for ollama, standard for openai/anthropic

## Shared Worker API

All three worker services expose the same HTTP API:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/work` | Receive task delegation from controller |
| GET | `/status` | Current worker status and task info |
| POST | `/push` | Push working directory to remote git |
| POST | `/free` | Delete working directory, return to free status |
| GET | `/files` | List files in working directory (recursive) |
| GET | `/files/{path:path}` | Read file content |
| GET | `/diff` | List changed files (git diff) |
| GET | `/diff/{path:path}` | Get diff for a specific file |
| GET | `/download` | Download working directory as zip archive |

## Data Model

### `worker_executions` table (worker-local)

Each worker maintains its own execution log in a separate table within the same PostgreSQL database.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| job_id | UUID | Task being executed |
| status | VARCHAR | free, in_progress, completed, failed |
| started_at | TIMESTAMPTZ | Execution start time |
| completed_at | TIMESTAMPTZ | Execution end time |
| error_message | TEXT | Error details if failed |

Worker uses upsert logic (select + update existing OR insert new) to handle retried tasks.

Each worker has its own Alembic migration (`worker_0001_create_worker_executions.py`) that runs on startup.

## Service Architecture

```
agents/{agent_name}/
├── Dockerfile
├── pyproject.toml
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/worker_0001_create_worker_executions.py
├── src/
│   ├── {agent_library}/     # Agent library (CodingAgent, OpenHandsAgent, etc.)
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── config.py
│   │   └── result.py
│   └── worker/              # Worker service (shared pattern)
│       ├── __init__.py
│       ├── app.py           # FastAPI app with lifespan (migrations, registration, heartbeat)
│       ├── config.py        # Settings: CONTROLLER_URL, AGENT_TYPE, WORK_DIR, WORKER_PORT
│       ├── agent_runner.py  # Bridges WorkRequest to agent library
│       ├── routes.py        # HTTP endpoints
│       ├── registration.py  # register_with_controller() + start_heartbeat_loop()
│       ├── git_utils.py     # inject_github_token(), clone_repository()
│       └── models.py        # WorkExecution ORM model
└── tests/
```

### Registration & Heartbeat

On startup:
1. Run Alembic migrations for `worker_executions` table
2. Call `POST /workers/register` on controller with `agent_type` and `worker_url`
3. Start background heartbeat loop (every 15 seconds, configurable)

Heartbeat loop:
- Sends `POST /workers/{worker_id}/heartbeat` with current status
- On 404 response: auto re-registers with controller (handles controller restarts)
- Accepts `agent_type` and `worker_url` for re-registration

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTROLLER_URL` | `http://controller:8003` | Controller service URL |
| `AGENT_TYPE` | varies per agent | Agent identifier matching DB `agents.identifier` |
| `WORK_DIR` | `/agent-work` | Base directory for working directories |
| `WORKER_PORT` | varies (8001/8004/8005) | Worker listen port |
| `HEARTBEAT_INTERVAL_SECONDS` | `15` | Heartbeat frequency |
| `WORKER_ID` | auto-assigned | Optional pre-set worker ID |
| `DATABASE_URL` | — | PostgreSQL connection for worker_executions |
| `TOOLS_GATEWAY_URL` | `http://tools:8002` | MCP tools gateway URL |
| `CORS_ORIGINS` | — | Allowed CORS origins for file browsing (dev: `http://localhost:3000`) |

## Cross-Context Dependencies

- **Orchestration**: Workers register with controller, receive delegations, send heartbeats
- **Task Lifecycle**: Workers execute tasks and update status via controller
- **Source Code Browser**: Workers expose `/files`, `/diff`, `/download` endpoints for browsing
- **Git Integration**: Workers handle clone and push operations
- **Platform Infrastructure**: Workers read agent settings from work payload; depend on MCP tools gateway
