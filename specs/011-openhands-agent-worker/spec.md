# Feature Specification: OpenHands Agent Worker

**Feature ID**: 011-openhands-agent-worker
**Created**: 2026-03-11
**Status**: Implemented

## Overview

Add a new agent worker based on the OpenHands SDK (`openhands-ai`) to the multi-agent system. The OpenHands agent provides terminal and file-editing capabilities via the OpenHands conversation framework, enabling autonomous coding tasks. The worker follows the same controller/worker architecture established in feature 009 and exposes the same source-code browsing endpoints from feature 010.

## User Scenarios

### User Story 1 — Submit a Task to the OpenHands Agent (Priority: P1)

A developer selects "OpenHands Agent" from the agent dropdown on the Submit Task page and submits a coding requirement. The controller delegates the task to the openhands worker, which runs the OpenHands SDK agent with terminal and file-editor tools. On completion, the task status updates to `completed` and the generated files are browsable in the Task Detail page.

**Acceptance Scenarios**:

1. **Given** the system is running with the openhands_agent worker registered, **When** the user submits a new task selecting "OpenHands Agent", **Then** the task is delegated to the openhands worker and begins execution.
2. **Given** the openhands worker receives a task, **When** the agent completes successfully, **Then** the task status transitions to `completed` and generated files are present in the working directory.
3. **Given** the agent encounters an error, **When** execution fails, **Then** the task status transitions to `failed` with an error message.

### User Story 2 — Browse Generated Files (Priority: P1)

After the OpenHands agent completes a task, the developer navigates to Task Detail and views the generated source code using the file browser and diff viewer, identical to the experience with other agent workers.

**Acceptance Scenarios**:

1. **Given** a completed openhands task, **When** the user opens Task Detail, **Then** the Source Code section loads files from the openhands worker (port 8005) without CORS errors.
2. **Given** the file browser is displayed, **When** the user clicks a file, **Then** the file content is rendered with syntax highlighting.
3. **Given** multiple workers running on different ports, **When** the frontend resolves the worker URL, **Then** it uses the `assigned_worker_url` from the task record (translated to localhost) rather than a hardcoded port.

### User Story 3 — Configure LLM Provider (Priority: P2)

The openhands agent supports ollama, OpenAI, and Anthropic LLM providers via the system settings. For ollama specifically, the agent uses prompt-based tool calling (`native_tool_calling=False`) since ollama models do not reliably support native function calling.

**Acceptance Scenarios**:

1. **Given** the LLM provider is set to "ollama" in settings, **When** the agent is invoked, **Then** the LLM is configured with the `ollama/` model prefix, the ollama base URL (without `/v1` suffix), and `native_tool_calling=False`.
2. **Given** the LLM provider is set to "anthropic" or "openai", **When** the agent is invoked, **Then** the LLM is configured with the appropriate API key and model prefix.

## Implementation Details

### Agent Library (`agents/openhands_agent/src/openhands_agent/`)

- **`agent.py`** — `OpenHandsAgent` class: builds an `openhands.sdk.LLM`, creates an `Agent` with `terminal` and `file_editor` tools, runs a `LocalConversation` in the task's working directory, and returns an `OpenHandsAgentResult`.
- **`config.py`** — `OpenHandsAgentConfig` frozen Pydantic model with fields: `project_name`, `requirement`, `working_directory`, `llm_provider`, `llm_model`, `llm_temperature`, `ollama_base_url`, `openai_api_key`, `anthropic_api_key`.
- **`result.py`** — `OpenHandsAgentResult` frozen dataclass: `code`, `summary`, `output_file`.

### Worker Service (`agents/openhands_agent/src/worker/`)

Follows the same pattern as `simple_crewai_pair_agent` worker:

- **`app.py`** — FastAPI application with lifespan (migrations, registration, heartbeat), CORS middleware.
- **`routes.py`** — REST endpoints: `/health`, `/work`, `/status`, `/download`, `/push`, `/free`, plus source-code browsing endpoints: `/files`, `/files/{path}`, `/diff`, `/diff/{path}`.
- **`agent_runner.py`** — Bridges worker request to `OpenHandsAgent`, persists execution state.
- **`config.py`** — `AGENT_TYPE="openhands_agent"`, `WORKER_PORT=8005`.
- **`registration.py`**, **`git_utils.py`**, **`models.py`** — Identical to the simple_crewai worker.

### Database

- **API migration `0011`** — Seeds `openhands_agent` row in the `agents` table (display name: "OpenHands Agent").
- **Worker migration `worker_0001`** — Creates `worker_executions` table (same schema as other workers).

### Docker Compose

- **`compose.yaml`** — `openhands_agent` service definition (image, depends_on, env_file, volumes).
- **`compose.dev.yaml`** — Dev overrides: port mapping `8005:8005`, source volume mounts, `PYTHONPATH`, `CORS_ORIGINS`.

### Frontend Fix (Multi-Worker URL Routing)

- **`web/src/lib/workerClient.ts`** — `getWorkerBaseUrl()` now prefers `assignedWorkerUrl` (rewriting the container hostname to `localhost`) over the `NEXT_PUBLIC_WORKER_URL` env var fallback. This enables the frontend to correctly route file-browsing requests to whichever worker ran the task.

## Key Technical Decisions

1. **OpenHands SDK API**: Uses `openhands.sdk.LLM`, `Agent`, `LocalConversation`, and `Tool`. Tool modules (`openhands.tools.terminal`, `openhands.tools.file_editor`) must be explicitly imported to trigger registration with the tool registry.
2. **Tool names**: The registered tool names are `"terminal"` and `"file_editor"` (not class names like `"TerminalTool"`).
3. **Ollama compatibility**: `native_tool_calling=False` is required for ollama models — without it, tool-call requests produce empty LLM responses. The `base_url` must not include a `/v1` suffix; litellm handles routing internally for `ollama/` prefixed models.
4. **CORS**: Each worker that serves file-browsing endpoints must have `CORSMiddleware` configured, since the browser calls the worker directly (not via the API proxy).
5. **Worker URL routing**: With multiple workers on different ports, the frontend cannot use a single hardcoded `NEXT_PUBLIC_WORKER_URL`. The `assigned_worker_url` from the task record (set by the controller during delegation) is the source of truth, with hostname rewritten to `localhost` for browser access.

## Files Created / Modified

### New files (initial implementation — commit `4dee7a8`)

```
agents/openhands_agent/
├── pyproject.toml
├── Dockerfile
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/worker_0001_create_worker_executions.py
├── src/
│   ├── openhands_agent/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── config.py
│   │   └── result.py
│   └── worker/
│       ├── __init__.py
│       ├── app.py
│       ├── config.py
│       ├── agent_runner.py
│       ├── routes.py
│       ├── registration.py
│       ├── git_utils.py
│       └── models.py
└── tests/
    ├── conftest.py
    ├── conftest_worker.py
    ├── test_agent_runner.py
    ├── test_routes.py
    ├── test_git_utils.py
    └── test_registration.py
api/alembic/versions/0011_add_openhands_agent.py
agents/pyproject.toml  (updated workspace members)
compose.yaml           (added openhands_agent service)
compose.dev.yaml       (added openhands_agent dev overrides)
```

### Bug fixes (post-implementation)

- `agent.py` — Remove `/v1` suffix from ollama `base_url` (commit `417f42e`)
- `agent.py` — Add `native_tool_calling=False` for ollama; register `terminal` + `file_editor` tools with correct names and imports
- `routes.py` — Add `/files`, `/files/{path}`, `/diff`, `/diff/{path}` endpoints for source-code browsing
- `app.py` — Add `CORSMiddleware` for browser-direct file requests
- `compose.dev.yaml` — Add `CORS_ORIGINS` env var for openhands service
- `workerClient.ts` — Fix multi-worker URL routing to use `assignedWorkerUrl` with hostname rewriting
