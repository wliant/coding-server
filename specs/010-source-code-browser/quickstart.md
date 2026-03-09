# Quickstart: Source Code Browser (010)

## Prerequisites

- Docker + Docker Compose running
- `task dev` environment started

## Development Setup

```bash
# 1. Start all services
task dev

# 2. After Phase 1 (worker changes) — rebuild and restart worker
docker compose -f compose.yaml -f compose.dev.yaml build worker
docker compose -f compose.yaml -f compose.dev.yaml up -d worker

# 3. Run worker tests (Phase 1 gate)
docker compose -f compose.yaml -f compose.dev.yaml exec worker pytest tests/test_routes_files.py -v

# 4. After Phase 2 (API schema change) — rebuild and restart api + migrate
docker compose -f compose.yaml -f compose.dev.yaml build api migrate
docker compose -f compose.yaml -f compose.dev.yaml up -d api

# 5. Regenerate TypeScript client (Phase 2 gate)
cd web && npm run generate

# 6. After Phase 3 (web dependency add) — install packages in web container
docker compose -f compose.yaml -f compose.dev.yaml exec web npm install

# 7. Run full test suite
task test-all

# 8. Run e2e tests (Phase 5 gate)
task e2e
```

## Manual Verification

1. Submit a new task and wait for it to complete
2. Navigate to `/tasks/{id}`
3. Scroll below the task detail panel — the **Source Code** section should appear
4. Verify the file tree renders all generated files
5. Click a `.py` or `.ts` file — content should appear with syntax highlighting
6. Click the **Download Code** button in the Source Code section — zip should download
7. Confirm the **Download Code** button is NOT present in the main task detail panel
8. Navigate to an `in_progress` task — the Source Code section should NOT be visible

## Key Environment Variables (compose.dev.yaml)

```yaml
# worker service
CORS_ORIGINS: "http://localhost:3000"

# web service
NEXT_PUBLIC_WORKER_URL: "http://localhost:8001"
```
