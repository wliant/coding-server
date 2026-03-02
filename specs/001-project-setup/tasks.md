---
description: "Task list for feature: Multi-Agent Software Development System — Initial Project Setup"
---

# Tasks: Multi-Agent Software Development System — Initial Project Setup

**Input**: Design documents from `/specs/001-project-setup/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/openapi.yaml ✅ quickstart.md ✅

**Organization**: Tasks grouped by user story for independent implementation and testing.
**Tests**: Included — pytest required by FR-010 (explicit requirement); e2e tests required by FR-003.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: User story label (US1–US4); omitted in Setup and Foundational phases

## Path Conventions

All paths relative to repository root (`coding-machine/`).

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Initialize directory layout and all four component project skeletons.

- [X] T001 Create root-level directory skeleton: `web/`, `api/`, `worker/`, `tools/`, `data/` (gitkeep), `agent-work/` (gitkeep), `specs/`; create root `.gitignore` covering `.env`, `data/`, `agent-work/`, `__pycache__/`, `.next/`, `node_modules/`, `*.pyc`, `.pytest_cache/`, `dist/`

- [X] T002 [P] Initialize `web/` as Next.js 15 App Router project: run `npx create-next-app@latest web --typescript --eslint --app --no-src-dir`; then move source into `web/src/` (App Router layout); enable strict mode in `web/tsconfig.json`; install `@hey-api/openapi-ts @hey-api/client-fetch`; add `"generate": "openapi-ts"` and `"prebuild": "npm run generate"` scripts to `web/package.json`

- [X] T003 [P] Initialize `api/` Python package with src layout: create `api/pyproject.toml` declaring `fastapi>=0.115`, `sqlalchemy[asyncio]>=2.0`, `asyncpg`, `alembic`, `redis>=5.0`, `uvicorn[standard]`, `pydantic-settings`; create `api/src/api/__init__.py`; create empty stubs `api/src/api/main.py`, `api/src/api/db.py`

- [X] T004 [P] Initialize `worker/` Python package with src layout: create `worker/pyproject.toml` declaring `langgraph>=0.2`, `langchain-mcp-adapters`, `langchain-anthropic`, `fastapi>=0.115`, `uvicorn[standard]`, `redis>=5.0`, `pydantic-settings`, `langgraph-checkpoint-postgres`; create `worker/src/worker/__init__.py`; create empty stubs `worker/src/worker/state.py`, `worker/src/worker/config.py`, `worker/src/worker/worker.py`

- [X] T005 [P] Initialize `tools/` Python package with src layout: create `tools/pyproject.toml` declaring `fastmcp>=2.0`, `pytest-asyncio`; create `tools/src/tools/__init__.py`, `tools/src/tools/servers/__init__.py`; create empty stubs `tools/src/tools/gateway.py`, `tools/src/tools/servers/filesystem_server.py`, `tools/src/tools/servers/git_server.py`, `tools/src/tools/servers/shell_server.py`

- [X] T006 [P] Create `Makefile` at repo root with placeholder targets: `dev`, `dev-down`, `e2e`, `prod`, `prod-down`, `generate`, `test-api`, `test-worker`, `test-tools`, `test-all`, `lint-api`, `logs`, `shell-api`; each target prints a "not yet implemented" message so `make` does not error

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required before any user story can be validated.
**⚠️ CRITICAL**: All Phase 3+ work is blocked until this phase is complete.

### Dockerfiles (parallel)

- [X] T007 [P] Create `web/Dockerfile` as multi-stage build: stage 1 `deps` (node:20-alpine, install only `package.json` deps); stage 2 `builder` (copy source, run `npm run build`); stage 3 `runner` (node:20-alpine, non-root user, copy `.next/standalone` and `.next/static`); expose port 3000; `CMD ["node", "server.js"]`

- [X] T008 [P] Create `api/Dockerfile`: base `python:3.12-slim`; install package via `pip install -e .`; create non-root user `appuser`; copy `src/` and `alembic/` and `scripts/`; expose port 8000; default `CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]`

- [X] T009 [P] Create `worker/Dockerfile`: base `python:3.12-slim`; install package via `pip install -e .`; create non-root user `appuser`; copy `src/`; expose port 8001; default `CMD ["uvicorn", "worker.worker:app", "--host", "0.0.0.0", "--port", "8001"]`

- [X] T010 [P] Create `tools/Dockerfile`: base `python:3.12-slim`; install package via `pip install -e .`; create non-root user `appuser`; copy `src/`; expose port 8002; default `CMD ["python", "-m", "tools.gateway"]`

### Health endpoints (parallel — required for depends_on: condition: service_healthy)

- [X] T011 [P] Create `api/src/api/routes/health.py` with `GET /health` router returning `HealthResponse` with `status` and `components` dict (initially returns `{"status": "ok", "components": {"database": "ok", "redis": "ok"}}` as a stub; full check added in T031)

- [X] T012 [P] Create `worker/src/worker/worker.py` with: a FastAPI app instance; `GET /health` endpoint returning `{"status": "ok"}`; a stubbed async `main_loop()` coroutine (BLMOVE skeleton, logs "worker ready"); lifespan context manager that starts `main_loop` as a background task via `asyncio.create_task`

- [X] T013 [P] Create `tools/src/tools/gateway.py`: instantiate a `FastMCP("tool-gateway")` app; add a `/health` HTTP route returning `{"status": "ok"}`; include `if __name__ == "__main__": mcp.run(transport="streamable-http", host="0.0.0.0", port=8002)`

- [X] T014 [P] Create `web/src/app/api/health/route.ts` exporting `GET` handler that returns `Response.json({ status: "ok" })` with status 200

### MCP tool server stubs (parallel)

- [X] T015 [P] Create `tools/src/tools/servers/filesystem_server.py`: instantiate `FastMCP("filesystem")`; add two stub tools: `read_file(path: str) -> str` and `write_file(path: str, content: str) -> None`; tools raise `NotImplementedError` for now

- [X] T016 [P] Create `tools/src/tools/servers/git_server.py`: instantiate `FastMCP("git")`; add stub tools: `git_clone(url: str, destination: str) -> str` and `git_status(repo_path: str) -> str`

- [X] T017 [P] Create `tools/src/tools/servers/shell_server.py`: instantiate `FastMCP("shell")`; add stub tool: `run_command(command: str, cwd: str) -> str` that raises `NotImplementedError`

- [X] T018 Mount all three tool servers in `tools/src/tools/gateway.py`: import each server's `mcp` instance; call `gateway_app.mount("filesystem", filesystem_mcp)`, `gateway_app.mount("git", git_mcp)`, `gateway_app.mount("shell", shell_mcp)` (depends on T013, T015, T016, T017)

### Database layer (api component)

- [X] T019 [P] Create `api/src/api/models/project.py` with SQLAlchemy 2.x `DeclarativeBase` subclass `Base`; define `Project` model with `mapped_column()` for: `id` (UUID, pk, server_default=func.gen_random_uuid()), `name` (String 255, not null), `source_type` (String 20, not null), `git_url` (Text, nullable), `status` (String 20, default "active"), `created_at` (TIMESTAMP WITH TIME ZONE, server_default=func.now()), `updated_at` (TIMESTAMP WITH TIME ZONE, server_default=func.now(), onupdate=func.now()); add `__tablename__ = "projects"`

- [X] T020 [P] Create `api/src/api/models/job.py` with `Job` model: `id` (UUID pk), `project_id` (UUID FK→projects.id, not null), `requirement` (Text not null), `status` (String 20 default "queued"), `created_at`, `started_at` (nullable), `completed_at` (nullable), `error_message` (Text nullable); and `WorkDirectory` model: `id` (UUID pk), `job_id` (UUID FK→jobs.id, unique, not null), `path` (Text not null unique), `created_at` (imports `Base` from models/project.py)

- [X] T021 Create `api/src/api/db.py`: import `create_async_engine`, `AsyncSession`, `async_sessionmaker`; read `DATABASE_URL` from env; create engine and session factory; define `async def get_db()` FastAPI dependency yielding `AsyncSession` (depends on T019, T020)

- [X] T022 Configure Alembic: create `api/alembic.ini` pointing to `api/alembic/`; create `api/alembic/env.py` using async engine from `api.db`; run `alembic revision --autogenerate -m "initial schema"` to generate `api/alembic/versions/<hash>_initial_schema.py` (depends on T019, T020, T021)

### FastAPI application wiring

- [X] T023 Complete `api/src/api/main.py`: create `FastAPI` app instance with `title`, `version`, `openapi_url="/openapi.json"`; add lifespan that initialises async DB engine and Redis client (from `api.services.redis_client`); include routers: `health.router`, stub `projects.router`, stub `jobs.router` from `api.src.api.routes.*` (depends on T011, T019, T021)

- [X] T024 [P] Create stub `api/src/api/routes/projects.py` with `GET /projects` (returns `[]`) and `POST /projects` (returns 501 Not Implemented); `GET /projects/{project_id}` (returns 404); `GET /projects/{project_id}/jobs` (returns `[]`); `POST /projects/{project_id}/jobs` (returns 501)

- [X] T025 [P] Create stub `api/src/api/routes/jobs.py` with `GET /jobs/{job_id}` (returns 404) and `GET /jobs/{job_id}/logs` (returns `[]`)

### OpenAPI contract export (Principle VI — non-negotiable gate)

- [X] T026 Create `api/scripts/export_openapi.py`: import `app` from `api.main`; call `json.dumps(app.openapi(), indent=2)`; write output to `openapi.json` at repository root; print confirmation message (depends on T023, T024, T025)

- [X] T027 Run `python api/scripts/export_openapi.py` from repo root; commit the resulting `openapi.json`; verify it is structurally consistent with `specs/001-project-setup/contracts/openapi.yaml` (depends on T026)

- [X] T028 Create `web/openapi-ts.config.ts` with `defineConfig({ client: "@hey-api/client-fetch", input: "../openapi.json", output: { path: "./src/client", format: "prettier" } })`; run `cd web && npm run generate` to produce `web/src/client/` (depends on T027)

### Base compose.yaml

- [X] T029 Create `compose.yaml` at repo root with all 6 services (no `ports:` in base — ports only in overlays): `web` (build: ./web, expose: 3000, depends_on: api: condition: service_healthy), `api` (build: ./api, expose: 8000, depends_on: migrate: condition: service_completed_successfully, redis: condition: service_healthy), `worker` (build: ./worker, expose: 8001, depends_on: api: condition: service_healthy, redis: condition: service_healthy, tools: condition: service_healthy), `tools` (build: ./tools, expose: 8002), `postgres` (image: postgres:16, healthcheck: pg_isready, expose: 5432), `redis` (image: redis:7-alpine, healthcheck: redis-cli ping, expose: 6379); add `migrate` one-shot service (build: ./api, command: alembic upgrade head, depends_on: postgres: condition: service_healthy, restart: "no"); declare top-level networks `backend` and top-level volumes skeleton (depends on T007-T014, T018, T023)

**Checkpoint**: Foundation complete — US1, US2, US3, US4 can now proceed independently.

---

## Phase 3: User Story 1 — Local Development Environment Startup (Priority: P1) 🎯 MVP

**Goal**: `make dev` brings up all 6 services; every health endpoint returns 200; web UI loads in a browser; individual services can be restarted without full teardown.

**Independent Test**: `docker compose -f compose.yaml -f compose.dev.yaml up` from a clean clone; verify `curl http://localhost:{8000,8001,8002}/health` and `curl http://localhost:3000/api/health` all return `{"status":"ok"}`; open browser to `http://localhost:3000`.

- [X] T030 [US1] Create `.env.example` listing all required variables with comments: `COMPOSE_PROJECT_NAME=madm_dev`, `WEB_PORT=3000`, `API_PORT=8000`, `WORKER_PORT=8001`, `TOOLS_PORT=8002`, `POSTGRES_PORT=5432`, `REDIS_PORT=6379`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `REDIS_URL=redis://redis:6379/0`, `AGENT_WORK_PARENT=/agent-work`, `TOOLS_GATEWAY_URL=http://tools:8002`; copy to `.env` with sensible development defaults

- [X] T031 [US1] Create `compose.dev.yaml` with overrides for all 6 services: `api` — override command to `uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/src`, bind mount `./api/src:/app/src`; `worker` — bind mount `./worker/src:/app/src`; `tools` — bind mount `./tools/src:/app/src`; `web` — override command to `npm run dev`, bind mounts `./web/src:/app/src` and `./web/public:/app/public`, anonymous volumes `/app/node_modules` and `/app/.next`, env `WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true`; `postgres` — bind mount `./data/postgres:/var/lib/postgresql/data`; `worker` — bind mount `./agent-work:/agent-work`; all services get `ports:` from `.env` variables (`"${API_PORT:-8000}:8000"` etc.); env_file: `.env` on all services

- [X] T032 [US1] Create `api/src/api/services/redis_client.py`: define `async def get_redis(request: Request)` dependency returning `request.app.state.redis`; update `api/src/api/main.py` lifespan to create `redis.asyncio.Redis.from_url(settings.REDIS_URL, decode_responses=True)` and store as `app.state.redis`, close on shutdown (depends on T023)

- [X] T033 [US1] Update `api/src/api/routes/health.py` to perform real health checks: `SELECT 1` via async SQLAlchemy session; `PING` via Redis client; return `{"status": "ok"|"degraded"|"unhealthy", "components": {"database": "ok"|"unavailable", "redis": "ok"|"unavailable", "worker": "ok"|"unavailable"}}`; catch exceptions and set component status to "unavailable" without raising; return HTTP 200 always (container health check must not fail on 5xx) (depends on T032)

- [X] T034 [US1] Create `worker/src/worker/config.py` with `class Settings(BaseSettings)` reading: `REDIS_URL`, `DATABASE_URL`, `AGENT_WORK_PARENT` (default `/agent-work`), `TOOLS_GATEWAY_URL`; instantiate `settings = Settings()` as module singleton

- [X] T035 [US1] Update `Makefile` `dev` target: `docker compose -f compose.yaml -f compose.dev.yaml --env-file .env up`; `dev-down` target: `docker compose -f compose.yaml -f compose.dev.yaml down`; `logs` target: `docker compose -f compose.yaml -f compose.dev.yaml logs -f`; `shell-api` target: `docker compose -f compose.yaml -f compose.dev.yaml exec api bash`

- [ ] T036 [US1] Validate User Story 1: run `make dev`; wait for all services to reach `healthy`; run `curl http://localhost:8000/health` (expect `{"status":"ok",...}`); run `curl http://localhost:3000/api/health` (expect `{"status":"ok"}`); run `curl http://localhost:8001/health` and `curl http://localhost:8002/health`; open browser to `http://localhost:3000`; stop `api` container and restart it; verify it rejoins without full restart; document any issues in quickstart.md Troubleshooting section

**Checkpoint**: User Story 1 complete — local dev environment fully functional.

---

## Phase 4: User Story 2 — End-to-End Test Execution (Priority: P2)

**Goal**: `make e2e` starts an isolated environment (separate ports + project name), runs Playwright tests against all 4 component boundaries, reports results, and tears down cleanly.

**Independent Test**: With `make dev` stopped, run `make e2e`; verify isolated containers start, tests run to completion with a pass/fail report covering web→api, api→postgres, api→redis, worker→tools boundaries, and environment is torn down after.

- [X] T037 [P] [US2] Create `.env.e2e` with: `COMPOSE_PROJECT_NAME=madm_e2e`, `WEB_PORT=3100`, `API_PORT=8100`, `WORKER_PORT=8101`, `TOOLS_PORT=8102`, `POSTGRES_PORT=5532`, `REDIS_PORT=6479`, same DB credentials as `.env`

- [X] T038 [P] [US2] Create `compose.e2e.yaml` with: all services get port mappings from `.env.e2e`; `postgres` and `worker` use anonymous volumes (no bind mounts); `api` and `worker` use production commands (not hot-reload); include a `test-runner` service (depends on web: service_healthy, api: service_healthy, worker: service_healthy, tools: service_healthy)

- [X] T039 [P] [US2] Create `web/tests/e2e/Dockerfile`: `FROM node:20-alpine`; install Playwright with `npx playwright install chromium --with-deps`; copy e2e test files; `CMD ["npx", "playwright", "test"]`

- [X] T040 [P] [US2] Create `web/tests/e2e/health.spec.ts` Playwright test suite: `test("api health endpoint returns ok")` — fetch `http://api:8000/health` and assert `status === "ok"`; `test("worker health endpoint returns ok")` — fetch `http://worker:8001/health`; `test("tools health endpoint returns ok")` — fetch `http://tools:8002/health`; `test("web health endpoint returns ok")` — navigate to `http://web:3000/api/health` and assert body contains `"ok"`

- [X] T041 [P] [US2] Create `web/tests/e2e/api-boundary.spec.ts` Playwright test suite: `test("GET /projects returns array")` — fetch `http://api:8000/projects`, assert response is JSON array; `test("GET /health returns component statuses")` — fetch `/health`, assert `components.database` and `components.redis` fields exist; add Playwright config `web/playwright.config.ts` with `baseURL: process.env.BASE_URL || "http://localhost:3000"`, `timeout: 30000`

- [X] T042 [US2] Complete `test-runner` service in `compose.e2e.yaml`: `build: context: ./web/tests/e2e`; environment variables pointing to service hostnames (`API_URL=http://api:8100`, `BASE_URL=http://web:3100`); `restart: "no"`; depends_on all 4 app services as `condition: service_healthy` (depends on T038, T039, T040, T041)

- [X] T043 [US2] Update `Makefile` `e2e` target: `docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e up --abort-on-container-exit --exit-code-from test-runner; docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e down -v`

- [ ] T044 [US2] Validate User Story 2: ensure `make dev` is stopped; run `make e2e`; observe isolated environment start; verify test results printed to stdout; verify exit code is 0; run again with dev environment running simultaneously to confirm port isolation works

**Checkpoint**: User Story 2 complete — e2e test suite runnable independently of dev environment.

---

## Phase 5: User Story 3 — Production Deployment (Priority: P3)

**Goal**: `make prod` starts all services in production mode (named volumes, restart policies, no debug tooling); data persists across restarts; no development settings exposed.

**Independent Test**: Run `make prod` in a clean environment; verify all health endpoints respond; restart with `docker compose ... restart`; verify data persists; inspect config to confirm no hot-reload or debug ports.

- [X] T045 [P] [US3] Create `compose.prod.yaml` with production overrides for all services: `api` — production uvicorn command (no `--reload`, add `--workers 2`); `web` — command `node server.js` (pre-built); `restart: unless-stopped` on all 6 services; named volumes `postgres_data:/var/lib/postgresql/data` and `agent_work:/agent-work`; resource limits via `deploy.resources.limits` (api: cpu 1.0 / mem 512m; worker: cpu 2.0 / mem 1g; web: cpu 0.5 / mem 256m; tools: cpu 0.5 / mem 256m; postgres: mem 512m; redis: mem 128m); logging config (driver: json-file, max-size: 10m, max-file: 3); NO host port mappings for postgres or redis (internal only); web exposed on port 80→3000, api on 8000→8000

- [X] T046 [US3] Add `migrate` service to `compose.prod.yaml` (identical to base but with `restart: "no"` and production DATABASE_URL); verify it runs before api via `condition: service_completed_successfully` (depends on T045)

- [X] T047 [US3] Declare top-level `volumes:` block in `compose.prod.yaml`: `postgres_data: driver: local` and `agent_work: driver: local` (depends on T045)

- [X] T048 [US3] Update `Makefile` `prod` target: `docker compose -f compose.yaml -f compose.prod.yaml up -d`; `prod-down` target: `docker compose -f compose.yaml -f compose.prod.yaml down` (with a note: do NOT use `-v` in prod)

- [ ] T049 [US3] Validate User Story 3: run `make prod`; wait for all services healthy; run health checks against all ports; create a test project via `curl -X POST http://localhost:8000/projects -d '{"name":"test","source_type":"new"}'`; run `make prod-down` then `make prod` again; verify the project record persists; inspect compose.prod.yaml to confirm no `--reload`, no debug ports, no bind mounts to source code

**Checkpoint**: User Story 3 complete — production deployment independently runnable and data-persistent.

---

## Phase 6: User Story 4 — Code Organisation Verification (Priority: P4)

**Goal**: Each component has clearly separated `src/` and `tests/` directories; running tests for one component does not modify production files; pytest runs per-component in isolation.

**Independent Test**: `cd api && pytest tests/` runs and passes without modifying anything in `api/src/`; same for `worker/` and `tools/`; `cd web && npx jest` passes; no production files have modified timestamps after any test run.

### pytest configuration (parallel)

- [X] T050 [P] [US4] Configure `api/` pytest in `api/pyproject.toml`: add `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `markers = ["unit: no I/O", "integration: requires services"]`; add dev dependencies `pytest>=8.0`, `pytest-asyncio`, `fakeredis[aioredis]>=2.0`, `testcontainers[postgres,redis]>=4.0`; create `api/tests/__init__.py` and `api/tests/unit/__init__.py` and `api/tests/integration/__init__.py`

- [X] T051 [P] [US4] Configure `worker/` pytest in `worker/pyproject.toml`: same `asyncio_mode = "auto"`, `testpaths = ["tests"]`; add `pytest>=8.0`, `pytest-asyncio`, `fakeredis[aioredis]>=2.0`, `langchain-core` (for FakeListChatModel); create `worker/tests/__init__.py`, `worker/tests/unit/__init__.py`, `worker/tests/integration/__init__.py`

- [X] T052 [P] [US4] Configure `tools/` pytest in `tools/pyproject.toml`: same `asyncio_mode = "auto"`, `testpaths = ["tests"]`; add `pytest>=8.0`, `pytest-asyncio`; create `tools/tests/__init__.py`, `tools/tests/unit/__init__.py`, `tools/tests/integration/__init__.py`

### conftest.py fixtures (parallel)

- [X] T053 [P] [US4] Create `api/tests/conftest.py` with: `@pytest.fixture async def fake_redis()` using `fakeredis.aioredis.FakeRedis(decode_responses=True)`; `@pytest.fixture async def db_session()` using `AsyncSession` against an in-memory SQLite (or testcontainers Postgres with scope="session") for integration tests

- [X] T054 [P] [US4] Create `worker/tests/conftest.py` with: `@pytest.fixture def base_state()` returning `AgentState` dict with test values; `@pytest.fixture def mock_llm()` returning a `MagicMock` with `invoke` returning `AIMessage(content="test")`; `@pytest.fixture async def fake_redis()` using `fakeredis.aioredis.FakeRedis`

- [X] T055 [P] [US4] Create `tools/tests/conftest.py` with: `@pytest.fixture async def filesystem_client()` using `async with Client(filesystem_mcp) as c: yield c` for in-process FastMCP testing

### Placeholder tests (parallel)

- [X] T056 [P] [US4] Create `api/tests/unit/test_health.py`: `def test_health_route_importable()` — assert `from api.routes.health import router; assert router is not None`; `async def test_health_returns_ok(fake_redis)` — assert the health check function returns a dict with `status` key

- [X] T057 [P] [US4] Create `worker/tests/unit/test_state.py`: `def test_agent_state_keys()` — import `AgentState` from `worker.state`; create an instance with required keys; assert `"job_id"` and `"requirement"` and `"messages"` are in the state; `def test_config_reads_env(monkeypatch)` — set env vars, instantiate `Settings`, assert values

- [X] T058 [P] [US4] Create `tools/tests/unit/test_filesystem_server.py`: `async def test_read_file_raises_not_implemented()` — call `read_file("/tmp/nonexistent")` and assert `NotImplementedError` is raised (confirming the stub is wired correctly and the tool is discoverable)

- [X] T059 [P] [US4] Create `tools/tests/integration/test_gateway.py`: `async def test_gateway_lists_tools(filesystem_client)` — `tools = await filesystem_client.list_tools(); names = [t.name for t in tools]; assert "read_file" in names` (tests gateway routing without HTTP server)

- [X] T060 [P] [US4] Create `web/tests/unit/health.test.ts` Jest test: `import { GET } from "../../src/app/api/health/route"` (use `jest.config.ts` with Next.js preset); `test("returns ok status", async () => { const res = await GET(new Request("/")); const body = await res.json(); expect(body.status).toBe("ok"); })`; create `web/jest.config.ts` with Next.js Jest configuration

### Makefile test targets

- [X] T061 [US4] Complete `Makefile` test targets: `test-api`: `docker compose -f compose.yaml -f compose.dev.yaml exec api pytest tests/`; `test-worker`: `... exec worker pytest tests/`; `test-tools`: `... exec tools pytest tests/`; `test-all`: runs test-api, test-worker, test-tools sequentially; each target exits non-zero if tests fail

- [ ] T062 [US4] Validate User Story 4: run `make test-api` — verify pass, check no files under `api/src/` have modified timestamps; run `make test-worker` — same check on `worker/src/`; run `make test-tools` — same on `tools/src/`; run `cd web && npx jest` — verify pass; browse repository and confirm each component has visually distinct `src/` and `tests/` subtrees

**Checkpoint**: User Story 4 complete — all components have independently runnable test suites with clean src/test separation.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Completeness, observability, and documentation.

- [X] T063 [P] Complete `Makefile` remaining targets: `generate` — `cd api && python scripts/export_openapi.py; cd web && npm run generate`; `lint-api` — `npx @redocly/cli lint openapi.json`; add `.PHONY` declaration for all targets; add a `help` target that prints all available targets with descriptions

- [X] T064 [P] Add structured JSON logging to all Python components: in `api/src/api/main.py` configure `logging.basicConfig` with a JSON formatter (use `python-json-logger` or manual formatter); log every request via middleware with `request_id`, `method`, `path`, `status_code`; in `worker/src/worker/worker.py` log each job lifecycle event (`job_id`, `event`, `timestamp`); add `python-json-logger` to `api/pyproject.toml` and `worker/pyproject.toml`

- [X] T065 [P] Add OpenAPI spec staleness CI check: create `api/scripts/check_openapi_fresh.sh` — runs `export_openapi.py` to a temp file, diffs against committed `openapi.json`, exits 1 if different; add `make check-openapi` target; document in quickstart.md that this must pass before merging any backend change

- [ ] T066 Follow the quickstart.md walkthrough end-to-end from a fresh clone: verify every step in `quickstart.md` succeeds exactly as written; fix any steps that fail or are missing; update Troubleshooting section with any findings

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; T002–T006 are all parallel
- **Foundational (Phase 2)**: Depends on Phase 1 completion; within Phase 2:
  - T007–T010 (Dockerfiles) parallel
  - T011–T017 (health endpoints + tool stubs) parallel
  - T018 depends on T013, T015, T016, T017
  - T019–T020 (models) parallel
  - T021 depends on T019, T020
  - T022 depends on T019, T020, T021
  - T023 depends on T022
  - T024 depends on T011, T019, T021
  - T025–T026 parallel (stub routes)
  - T027 depends on T023, T024, T025, T026
  - T028 depends on T027
  - T029 depends on T007–T014, T018, T023
- **US1 (Phase 3)**: Depends on Phase 2 completion — BLOCKS nothing (independent)
- **US2 (Phase 4)**: Depends on Phase 2 completion — independent of US1
- **US3 (Phase 5)**: Depends on Phase 2 completion — independent of US1, US2
- **US4 (Phase 6)**: Depends on Phase 2 completion — independent of US1, US2, US3
- **Polish (Final)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on other stories
- **US2 (P2)**: Can start after Phase 2 — no dependency on US1
- **US3 (P3)**: Can start after Phase 2 — no dependency on US1, US2
- **US4 (P4)**: Can start after Phase 2 — no dependency on US1, US2, US3

### Parallel Opportunities Within Each Story

All four user stories (Phase 3–6) can be worked in parallel once Phase 2 is complete.

---

## Parallel Execution Examples

### Within Phase 2 (Foundational)

```bash
# Launch all Dockerfile tasks simultaneously:
Task: "Create web/Dockerfile" (T007)
Task: "Create api/Dockerfile" (T008)
Task: "Create worker/Dockerfile" (T009)
Task: "Create tools/Dockerfile" (T010)

# Launch all health endpoint tasks simultaneously:
Task: "Create api health route" (T011)
Task: "Create worker health app" (T012)
Task: "Create tools gateway with health" (T013)
Task: "Create Next.js health route" (T014)

# Launch all tool stub tasks simultaneously:
Task: "Create filesystem_server.py" (T015)
Task: "Create git_server.py" (T016)
Task: "Create shell_server.py" (T017)
```

### Once Phase 2 is complete

```bash
# All four user story phases can run simultaneously:
Task: "Work on US1 (Local Dev) Phase 3: T030→T036"
Task: "Work on US2 (E2E Tests) Phase 4: T037→T044"
Task: "Work on US3 (Production) Phase 5: T045→T049"
Task: "Work on US4 (Code Org) Phase 6: T050→T062"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T006)
2. Complete Phase 2: Foundational (T007–T029) — **CRITICAL, blocks all stories**
3. Complete Phase 3: User Story 1 (T030–T036)
4. **STOP and VALIDATE**: Run `make dev`, verify all health endpoints, open browser
5. Confirm: local dev environment works end-to-end

### Incremental Delivery

1. Phase 1 + Phase 2 → All Dockerfiles, health endpoints, base compose ready
2. Phase 3 → `make dev` works → **MVP delivered**
3. Phase 4 → `make e2e` works → **Test confidence delivered**
4. Phase 5 → `make prod` works → **Production-ready delivered**
5. Phase 6 → pytest per-component, clean src/test layout → **Code quality gate delivered**

### Parallel Team Strategy

With four developers after Phase 2 is complete:

- Developer A: Phase 3 (US1 — Local Dev)
- Developer B: Phase 4 (US2 — E2E Tests)
- Developer C: Phase 5 (US3 — Production)
- Developer D: Phase 6 (US4 — Code Organisation)

Each developer works independently; merge order: US1 → US2 → US3 → US4.

---

## Notes

- `[P]` tasks operate on different files with no pending dependencies — safe to run in parallel
- `[Story]` label maps each task to its user story for traceability
- OpenAPI export (T026–T028) is a hard gate per Principle VI — must complete before any route implementation proceeds beyond stubs
- The `migrate` one-shot service handles DB schema; never run `alembic upgrade head` manually against production
- `docker compose down --volumes` MUST NOT be used in production; it destroys named volumes
- Anonymous volumes in compose.e2e.yaml ensure a clean state for every e2e run without `--volumes`
- All health endpoints return HTTP 200 even when components are degraded — Docker health checks must not get 5xx
- `WATCHPACK_POLLING=true` is required in compose.dev.yaml for reliable hot reload on Linux Docker hosts
