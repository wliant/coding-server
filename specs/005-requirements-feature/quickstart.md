# Quickstart: Automated Task Execution via Agent Worker

**Feature**: 005-requirements-feature | **Date**: 2026-03-06

## Prerequisites

- Docker + Docker Compose installed
- Ollama running locally with a compatible model (default: `qwen2.5-coder:7b`)
  - Or credentials for an OpenAI / Anthropic provider
- Access to a remote git repository the server can push to (SSH key or token pre-configured)

---

## 1. Configure LLM Environment Variables

Create or extend `worker/.env` (or set in `compose.dev.yaml` under the `worker` service):

```env
# LLM Provider (ollama | openai | anthropic)
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:7b
OLLAMA_BASE_URL=http://host.docker.internal:11434

# If using OpenAI:
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4o
# OPENAI_API_KEY=sk-...

# If using Anthropic:
# LLM_PROVIDER=anthropic
# LLM_MODEL=claude-sonnet-4-6
# ANTHROPIC_API_KEY=sk-ant-...

# Worker tuning (optional — these are the defaults)
POLL_INTERVAL_SECONDS=5
LEASE_TTL_SECONDS=300
LEASE_RENEWAL_INTERVAL_SECONDS=120
```

---

## 2. Start the Dev Environment

```bash
task dev
```

This starts all services: postgres, redis, migrate, tools, api, worker, web.

---

## 3. Apply the Database Migration

The migration runs automatically on startup via the `migrate` service. To run manually:

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec api alembic upgrade head
```

This applies migration `0004` which adds `lease_holder` and `lease_expires_at` to the `jobs` table.

---

## 4. Submit a Task (end-to-end test)

1. Open the web UI at http://localhost:3000
2. Navigate to **New Task**
3. Fill in:
   - **Project**: New Project
   - **Git URL**: `https://github.com/your-org/your-repo.git` (or SSH URL)
   - **Requirements**: `Add a Python function that reverses a string`
   - **Dev Agent**: Spec Driven Development Agent
   - **Test Agent**: Generic Testing Agent
4. Click **Submit** → task appears in the list with status **Pending**
5. The worker picks it up within 5 seconds → status changes to **In Progress**
6. Click the task to open the **Task Detail** page — elapsed time is shown
7. When complete → status changes to **Completed**

---

## 5. Push Changes to Remote Git

1. From the Task Detail page of a **Completed** task, click **Push to Remote**
2. The system force-pushes a new branch `task/<short-id>` to the configured git URL
3. On success, the branch name and remote URL are confirmed in the UI

---

## 6. Run Tests

```bash
# API tests
docker compose -f compose.yaml -f compose.dev.yaml exec api pytest tests/

# Worker tests
docker compose -f compose.yaml -f compose.dev.yaml exec worker pytest tests/

# E2E tests
task e2e
```

---

## 7. Regenerate the TypeScript Client (after API changes)

```bash
task generate
```

This updates `web/src/client/` from the committed `openapi.json`.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Task stuck in Pending | Worker not running or LLM env vars missing | Check `docker compose logs worker`; verify `LLM_PROVIDER` and model env vars |
| Task stuck in In Progress | Worker crashed; waiting for lease to expire | Wait `LEASE_TTL_SECONDS` (default 5 min) for auto-requeue, or restart worker |
| Push fails with auth error | Git credentials not configured in server | Ensure SSH key or token is mounted/set in the container environment |
| Push fails: no git_url | Project was created without a git URL | Edit the project to add a git URL, or resubmit the task with a git URL |
| Agent error in task detail | LLM model not available | Verify Ollama is running and model is pulled (`ollama pull qwen2.5-coder:7b`) |
