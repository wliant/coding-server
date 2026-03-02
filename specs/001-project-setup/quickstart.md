# Quickstart: Multi-Agent Software Development System

**Branch**: `001-project-setup` | **Date**: 2026-03-02

---

## Prerequisites

- Docker Engine 24+ and Docker Compose v2 (`docker compose` as a plugin, not `docker-compose`)
- Git
- Make (optional but recommended for the shorthand commands)

No language runtimes (Python, Node.js) are required on the host — all code runs inside containers.

---

## Initial Setup (one time)

```bash
# 1. Clone the repository
git clone <repo-url> coding-machine
cd coding-machine

# 2. Create required host directories for dev bind mounts
mkdir -p ./data/postgres ./agent-work

# 3. Copy the dev environment file (edit if you have port conflicts)
cp .env.example .env
```

---

## Local Development

### Start all services

```bash
# Using Make (recommended)
make dev

# Or directly
docker compose -f compose.yaml -f compose.dev.yaml --env-file .env up
```

All six services start: `web`, `api`, `worker`, `tools`, `postgres`, `redis`.
A one-shot `migrate` service runs Alembic migrations before `api` starts.

**Expected output**: all services reach healthy state within 60 seconds of the command completing.

### Verify the environment is healthy

```bash
# Check all containers are running and healthy
docker compose -f compose.yaml -f compose.dev.yaml ps

# Hit each health endpoint directly
curl http://localhost:8000/health    # API backend
curl http://localhost:3000/api/health  # Next.js web interface
curl http://localhost:8001/health    # LangGraph worker
curl http://localhost:8002/health    # FastMCP tool gateway
```

All should return `{"status": "ok", ...}`.

### Access the web interface

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Default ports (local dev)

| Service | Host Port | Description |
|---------|-----------|-------------|
| web | 3000 | Next.js web interface |
| api | 8000 | FastAPI backend (also serves `/docs` and `/redoc`) |
| worker | 8001 | Worker health endpoint |
| tools | 8002 | FastMCP tool gateway health endpoint |
| postgres | 5432 | PostgreSQL (accessible from host for local DB tools) |
| redis | 6379 | Redis (accessible from host for debugging) |

### API documentation (dev only)

| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/openapi.json | Raw OpenAPI spec |

### Hot reload

Both the FastAPI backend and the Next.js frontend support hot reload in dev mode:

- **Backend** (`api/`): edit any file under `api/src/` — Uvicorn reloads automatically.
- **Frontend** (`web/`): edit any file under `web/src/` — Next.js HMR updates the browser.
- **Worker** (`worker/`): restart the worker container after changes: `docker compose -f compose.yaml -f compose.dev.yaml restart worker`.
- **Tools** (`tools/`): restart the tools container after changes: `docker compose -f compose.yaml -f compose.dev.yaml restart tools`.

### Stop the environment

```bash
make dev-down
# or
docker compose -f compose.yaml -f compose.dev.yaml down
```

Data in `./data/postgres` and `./agent-work` is preserved on the host between restarts.

---

## Running Tests

### Per-component unit/integration tests (no Docker required)

Each Python component has its own test suite runnable with pytest from the host if you have
the component's dependencies installed, or inside its container:

```bash
# Run API tests inside the running container
docker compose -f compose.yaml -f compose.dev.yaml exec api pytest tests/

# Run worker tests
docker compose -f compose.yaml -f compose.dev.yaml exec worker pytest tests/

# Run tools tests
docker compose -f compose.yaml -f compose.dev.yaml exec tools pytest tests/
```

Or use Make shortcuts:

```bash
make test-api       # runs pytest in the api container
make test-worker    # runs pytest in the worker container
make test-tools     # runs pytest in the tools container
make test-all       # runs all component tests sequentially
```

### End-to-end tests (isolated environment)

The e2e environment uses port offsets to avoid clashing with a running dev environment:

```bash
# Using Make (recommended — starts env, runs tests, tears down)
make e2e

# Or manually
docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e up --abort-on-container-exit
docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e down -v
```

The e2e Compose file includes a `test-runner` service that runs the Playwright test suite against
the fully started environment. Exit code reflects test pass/fail.

**E2E port offsets** (configured in `.env.e2e`):

| Service | E2E Port |
|---------|----------|
| web | 3100 |
| api | 8100 |
| worker | 8101 |
| tools | 8102 |
| postgres | 5532 |
| redis | 6479 |

---

## Generating the API Client (frontend)

When backend API routes change, regenerate the TypeScript client:

```bash
make generate
# which runs:
#   cd api && python scripts/export_openapi.py   → updates openapi.json at repo root
#   cd web && npm run generate                   → regenerates web/src/client/
```

The `openapi.json` at the repo root must be committed alongside any backend route change.
CI will fail if the committed `openapi.json` is stale relative to the FastAPI route definitions.

---

## Production Deployment

### Start production environment

```bash
make prod
# or
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

Production differences from dev:
- No bind mounts; source code is baked into images.
- No hot reload, debug ports, or development middleware.
- Named Docker volumes (`postgres_data`, `agent_work`) for persistent data.
- `restart: unless-stopped` on all services.
- Resource limits applied to each container.

### Verify production health

```bash
docker compose -f compose.yaml -f compose.prod.yaml ps
docker compose -f compose.yaml -f compose.prod.yaml exec api curl http://localhost:8000/health
```

### Data persistence

Production data survives `docker compose down` (containers removed) because it is stored in named
Docker volumes. **Warning**: `docker compose down --volumes` removes named volumes and destroys all
data. Do not use `--volumes` on a production deployment.

### Updating a running production deployment

```bash
# Pull new images (or rebuild if building locally)
docker compose -f compose.yaml -f compose.prod.yaml pull

# Recreate only changed services (zero-downtime for stateless services)
docker compose -f compose.yaml -f compose.prod.yaml up -d --no-deps api web worker tools
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `postgres` never becomes healthy | `./data/postgres` owned by root | `sudo chown -R $USER:$USER ./data/postgres` |
| Port already in use on startup | Another process on 3000/8000/etc. | Edit `.env` to change port numbers |
| Next.js hot reload not working | inotify event propagation issue | Add `WATCHPACK_POLLING=true` to `.env` (already set by default) |
| Worker not picking up jobs | Redis not healthy when worker started | Restart worker: `docker compose ... restart worker` |
| Migration fails on first run | `./data/postgres` has leftover partial init | Delete `./data/postgres/*` and restart |
| E2E tests conflict with running dev | Port collision | Dev and e2e use different ports; check `.env` vs `.env.e2e` |

---

## Make Command Reference

| Command | Description |
|---------|-------------|
| `make dev` | Start local development environment |
| `make dev-down` | Stop and remove dev containers (data preserved) |
| `make e2e` | Run full end-to-end test suite in isolated environment |
| `make prod` | Start production environment (detached) |
| `make generate` | Export OpenAPI spec + regenerate TypeScript client |
| `make test-api` | Run API component tests |
| `make test-worker` | Run worker component tests |
| `make test-tools` | Run tools component tests |
| `make test-all` | Run all component tests |
| `make logs` | Tail logs from all dev services |
| `make shell-api` | Open a shell in the running api container |
