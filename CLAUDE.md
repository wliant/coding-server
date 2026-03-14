# coding-machine Development Guidelines

Last updated: 2026-03-14

## Active Technologies

- **Backend (api)**: Python 3.12, FastAPI 0.115+, SQLAlchemy 2 async, asyncpg, Alembic
- **Frontend (web)**: TypeScript, Node.js 20, Next.js 15 App Router, React 19, Tailwind CSS, shadcn/ui, @hey-api/client-fetch
- **Workers**: Python 3.12; CrewAI (port 8001), LangChain (port 8004), OpenHands (port 8005)
- **Sandbox**: Python 3.12, general-purpose execution environment (port 8006)
- **Tools**: Python 3.12, FastMCP
- **Database**: PostgreSQL 16 (tables: projects, jobs, agents, settings, work_directories, sandboxes)
- **Cache/Queue**: Redis

## Project Structure

```text
coding-machine/
├── compose.yaml / compose.dev.yaml / compose.e2e.yaml / compose.prod.yaml
├── openapi.json          # committed OpenAPI spec (source of truth for client gen)
├── Taskfile.yml          # cross-platform task runner
├── specs/                # bounded-context specifications
│   ├── task-lifecycle/spec.md
│   ├── orchestration/spec.md
│   ├── agent-execution/spec.md
│   ├── source-code-browser/spec.md
│   ├── git-integration/spec.md
│   └── platform-infrastructure/spec.md
├── web/                  # Next.js 15 web interface
│   ├── src/
│   └── tests/
├── api/                  # FastAPI backend
│   ├── src/api/
│   ├── tests/
│   └── alembic/
├── agents-controller/    # FastAPI service coordinating agents (port 8003)
│   ├── src/controller/
│   └── tests/
├── tools/                # FastMCP tool servers
│   ├── src/tools/servers/
│   └── tests/
├── sandbox/              # General-purpose execution environment (port 8006)
│   └── src/sandbox/
└── agents/               # Agent packages (uv workspace); each is a self-contained deployable unit
    ├── simple_crewai_pair_agent/  # CrewAI pair agent + worker (port 8001, implemented)
    │   ├── Dockerfile
    │   ├── alembic/
    │   ├── src/
    │   │   ├── simple_crewai_pair_agent/  # agent library
    │   │   └── worker/                    # worker service (FastAPI)
    │   └── tests/
    ├── simple_langchain_deepagent/ # LangChain agent + worker (port 8004)
    ├── openhands_agent/           # OpenHands agent + worker (port 8005)
    └── crewai_coding_team/        # Multi-agent team (stub)
```

## Commands

```bash
# Start local dev environment
task dev

# Run all component tests
task test-all

# Run per-component tests (inside container)
docker compose -f compose.yaml -f compose.dev.yaml exec api pytest tests/
docker compose -f compose.yaml -f compose.dev.yaml exec simple_crewai_pair_agent pytest tests/
docker compose -f compose.yaml -f compose.dev.yaml exec controller pytest tests/
docker compose -f compose.yaml -f compose.dev.yaml exec tools pytest tests/

# Run e2e tests
task e2e

# View service logs
task logs

# Regenerate OpenAPI spec + TypeScript client
task generate

# Lint Python (ruff)
cd api && ruff check src/
cd agents/simple_crewai_pair_agent && ruff check src/
cd tools && ruff check src/
cd agents-controller && ruff check src/

# Type-check frontend
cd web && npx tsc --noEmit
```

## Code Style

- **Python** (api, worker, tools): ruff for linting/formatting; type hints required on all public functions; `src/` layout (package under `src/`); pytest + pytest-asyncio for all tests; `asyncio_mode = "auto"` in pyproject.toml
- **TypeScript** (web): strict mode enabled; generated client code in `src/client/` (do not hand-edit); Prettier for formatting

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

## Recent Changes
- Specs reorganized into bounded-context subfolders (task-lifecycle, orchestration, agent-execution, source-code-browser, git-integration, platform-infrastructure)
- 011-sandbox-capabilities: Sandbox service (port 8006) with file CRUD, command execution, SSE streaming; SandboxRegistry on controller; `/sandboxes` UI page
- 011-openhands-agent-worker: OpenHands agent + worker (port 8005); multi-worker URL routing in frontend
- 011-task-types: 6 task types with cross-field validation; task type badges in UI
- 010-source-code-browser: File tree, file viewer, diff viewer on worker; browser-direct calls via assigned_worker_url
- 009-agent-controller-worker: Controller/worker architecture; heartbeat + lease pattern; cleanup flow; workers page
