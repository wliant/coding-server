# coding-machine Development Guidelines

Last updated: 2026-03-07

## Active Technologies

- **Backend (api)**: Python 3.12, FastAPI 0.115+, SQLAlchemy 2 async, asyncpg, Alembic
- **Frontend (web)**: TypeScript, Node.js 20, Next.js 15 App Router, React 19, Tailwind CSS, shadcn/ui, @hey-api/client-fetch
- **Worker**: Python 3.12, CrewAI (via simple_crewai_pair_agent)
- **Tools**: Python 3.12, FastMCP
- **Database**: PostgreSQL 16 (tables: projects, jobs, agents, settings, work_directories)
- **Cache/Queue**: Redis

## Project Structure

```text
coding-machine/
├── compose.yaml / compose.dev.yaml / compose.e2e.yaml / compose.prod.yaml
├── openapi.json          # committed OpenAPI spec (source of truth for client gen)
├── Taskfile.yml          # cross-platform task runner
├── specs/spec.md         # consolidated system specification
├── web/                  # Next.js 15 web interface
│   ├── src/
│   └── tests/
├── api/                  # FastAPI backend
│   ├── src/api/
│   ├── tests/
│   └── alembic/
├── worker/               # Background job processor
│   ├── src/worker/
│   └── tests/
├── tools/                # FastMCP tool servers
│   ├── src/tools/servers/
│   └── tests/
└── agents/               # Agent libraries (uv workspace)
    ├── simple_crewai_pair_agent/  # CrewAI pair agent (implemented)
    ├── crewai_coding_team/        # Multi-agent team (stub)
    └── simple_langchain_deepagent/ # LangChain agent (stub)
```

## Commands

```bash
# Start local dev environment
task dev

# Run all component tests
task test-all

# Run per-component tests (inside container)
docker compose -f compose.yaml -f compose.dev.yaml exec api pytest tests/
docker compose -f compose.yaml -f compose.dev.yaml exec worker pytest tests/
docker compose -f compose.yaml -f compose.dev.yaml exec tools pytest tests/

# Run e2e tests
task e2e

# Regenerate OpenAPI spec + TypeScript client
task generate

# Lint Python (ruff)
cd api && ruff check src/
cd worker && ruff check src/
cd tools && ruff check src/

# Type-check frontend
cd web && npx tsc --noEmit
```

## Code Style

- **Python** (api, worker, tools): ruff for linting/formatting; type hints required on all public functions; `src/` layout (package under `src/`); pytest + pytest-asyncio for all tests; `asyncio_mode = "auto"` in pyproject.toml
- **TypeScript** (web): strict mode enabled; generated client code in `src/client/` (do not hand-edit); Prettier for formatting

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

## Recent Changes
- 009-agent-controller-worker: Added Python 3.12 (controller, worker); TypeScript / Node.js 20 (web) + FastAPI 0.115+, SQLAlchemy 2 async, asyncpg, pydantic-settings, python-json-logger, httpx (controller and worker); simple-crewai-pair-agent, gitpython (worker); Next.js 15, React 19, Tailwind CSS, shadcn/ui, @hey-api/client-fetch (web)
