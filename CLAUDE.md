# coding-machine Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-02

## Active Technologies
- Python 3.12 (api), TypeScript / Node.js 20 (web) + FastAPI 0.115+ / SQLAlchemy 2 async / asyncpg / Alembic (api); Next.js 15 App Router / React 19 / Tailwind CSS / shadcn/ui / @hey-api/client-fetch (web) (002-task-management-ui)
- PostgreSQL 16 — existing `jobs` and `projects` tables extended; new `settings` table added via migration `0002` (002-task-management-ui)

- Python 3.12 (api, worker, tools); TypeScript / Node.js 20 (web) (001-project-setup)

## Project Structure

```text
coding-machine/
├── compose.yaml / compose.dev.yaml / compose.e2e.yaml / compose.prod.yaml
├── openapi.json          # committed OpenAPI spec (source of truth for client gen)
├── Makefile
├── web/                  # Next.js 15 web interface
│   ├── src/
│   └── tests/
├── api/                  # FastAPI backend
│   ├── src/api/
│   ├── tests/
│   └── alembic/
├── worker/               # LangGraph agent worker
│   ├── src/worker/
│   └── tests/
└── tools/                # FastMCP tool servers
    ├── src/tools/servers/
    └── tests/
```

## Commands

```bash
# Start local dev environment
make dev

# Run all component tests
make test-all

# Run per-component tests (inside container)
docker compose -f compose.yaml -f compose.dev.yaml exec api pytest tests/
docker compose -f compose.yaml -f compose.dev.yaml exec worker pytest tests/
docker compose -f compose.yaml -f compose.dev.yaml exec tools pytest tests/

# Run e2e tests
make e2e

# Regenerate OpenAPI spec + TypeScript client
make generate

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

## Recent Changes
- 002-task-management-ui: Added Python 3.12 (api), TypeScript / Node.js 20 (web) + FastAPI 0.115+ / SQLAlchemy 2 async / asyncpg / Alembic (api); Next.js 15 App Router / React 19 / Tailwind CSS / shadcn/ui / @hey-api/client-fetch (web)

- 001-project-setup: Added Python 3.12 (api, worker, tools); TypeScript / Node.js 20 (web)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
