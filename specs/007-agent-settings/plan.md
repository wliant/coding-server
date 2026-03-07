# Implementation Plan: Agent Settings Configuration

**Branch**: `007-agent-settings` | **Date**: 2026-03-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-agent-settings/spec.md`

## Summary

Add an "Agent Settings" tab to the Settings page that allows operators to configure `simple_crewai_pair_agent`'s LLM settings (provider, model, temperature, Ollama URL, OpenAI key, Anthropic key) via the UI. Settings are persisted in the existing `settings` key/value DB table. The worker fetches these settings via the API's `GET /settings` endpoint at job-execution time, replacing the current LLM environment-variable approach. The agent library is updated to always use the caller-provided config object (removing env var fallback).

## Technical Context

**Language/Version**: Python 3.12 (api, worker, agent); TypeScript / Node.js 20 (web)
**Primary Dependencies**: FastAPI 0.115+, SQLAlchemy 2 async, asyncpg, httpx (new, worker), Next.js 15, React 19, Tailwind CSS, shadcn/ui, @hey-api/client-fetch
**Storage**: PostgreSQL 16 — existing `settings` table; no new migration required
**Testing**: pytest + pytest-asyncio (`asyncio_mode = "auto"`) for api/worker/agent; Playwright for e2e
**Target Platform**: Linux containers (Docker Compose)
**Project Type**: Multi-service web application (api + worker + web + agent library)
**Performance Goals**: N/A — settings page is low-traffic; worker settings fetch adds one HTTP call per job
**Constraints**: No new DB table; no Alembic migration; OpenAPI spec updated with PATCH version bump; LLM env vars removed from worker
**Scale/Scope**: Single-tenant operator tool; 7 total settings keys after this feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Simplicity-First | ✅ PASS | Reuses existing settings table, route, service, and schema. One new component, no new abstractions. |
| II. TDD (NON-NEGOTIABLE) | ✅ PASS | Tests written before implementation in all tasks. Red-green-refactor cycle enforced per task. |
| III. Modularity | ✅ PASS | Changes isolated to `api/services/setting_service.py`, `worker/agent_runner.py` + `config.py`, new `web/components/settings/AgentSettings.tsx`. No cross-package imports added. |
| IV. Observability | ✅ PASS | Worker logs settings fetch failure (ERROR with job_id + error). API keys MUST NOT appear in logs (enforced in implementation tasks). |
| V. Incremental Delivery | ✅ PASS | 3 independent user stories. Story 1 (UI + API persistence) is viable MVP; stories 2 and 3 add provider switching and validation. |
| VI. API-First with OpenAPI (NON-NEGOTIABLE) | ✅ PASS | No endpoint schema change. `openapi.json` info.version receives a PATCH bump and description updated. TypeScript client regenerated after openapi.json update. |

**Post-Phase 1 re-check**: All principles still satisfied. No new violations introduced by design artifacts.

## Project Structure

### Documentation (this feature)

```text
specs/007-agent-settings/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── settings-api.md  # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code Changes (repository root)

```text
# API (Python — settings service expansion)
api/src/api/services/setting_service.py   # expand ALLOWED_KEYS, DEFAULTS, add validation
api/tests/unit/test_setting_service.py    # new tests for 6 keys + validation
api/tests/integration/test_settings_api.py # new integration tests
openapi.json                               # PATCH version bump + description update

# Worker (Python — read settings from API, remove LLM env vars)
worker/src/worker/config.py               # remove LLM fields, add API_URL
worker/src/worker/agent_runner.py         # fetch settings via httpx before agent run
worker/pyproject.toml                     # add httpx dependency
worker/tests/unit/test_agent_runner.py    # update tests (mock httpx, remove settings arg)
compose.yaml                              # remove LLM env vars from worker service, add API_URL

# Agent library (remove env var workaround)
agents/simple_crewai_pair_agent/src/simple_crewai_pair_agent/agent.py  # fix OPENAI_API_KEY setdefault

# Web (TypeScript — new Agent Settings tab)
web/src/components/settings/AgentSettings.tsx   # new component
web/src/app/settings/page.tsx                   # add Agent Settings tab
web/src/client/                                  # regenerate after openapi.json update
```

**Structure Decision**: Multi-service web application. Changes span api, worker, agent library, and web — all within the existing repo layout documented in CLAUDE.md.

## Phase 0: Research

Research consolidated in [research.md](./research.md). All decisions resolved:

1. **HTTP client**: `httpx[asyncio]` added to worker — async-first, consistent with FastAPI ecosystem.
2. **API URL**: New `API_URL` worker config field (`http://localhost:8000` default; `http://api:8000` in compose).
3. **Temperature validation**: In `setting_service.upsert_settings` — consistent with existing key validation pattern.
4. **Provider validation**: Enum check `{"ollama", "openai", "anthropic"}` in service layer.
5. **API key masking**: Frontend shows `••••••••` when stored value is non-empty; API returns plain text.
6. **LLM env vars**: Removed from `worker/config.py` and `compose.yaml`; settings store is sole source.
7. **OPENAI_API_KEY workaround**: Changed from `setdefault` to always-overwrite from config with `"PLACEHOLDER"` fallback.
8. **OpenAPI**: PATCH version bump + description update; no schema change; client regenerated.

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](./data-model.md) for full detail.

**Summary**: No new tables. 6 new keys in the existing `settings` table:
- `agent.simple_crewai.llm_provider` (default: `"ollama"`)
- `agent.simple_crewai.llm_model` (default: `"qwen2.5-coder:7b"`)
- `agent.simple_crewai.llm_temperature` (default: `"0.2"`)
- `agent.simple_crewai.ollama_base_url` (default: `"http://localhost:11434"`)
- `agent.simple_crewai.openai_api_key` (default: `""`)
- `agent.simple_crewai.anthropic_api_key` (default: `""`)

### API Contract

See [contracts/settings-api.md](./contracts/settings-api.md).

The `GET /settings` and `PUT /settings` endpoint shapes are unchanged (`dict[str, str]`). New validation rules added in service layer for provider enum and temperature range.

### Implementation Sequence

Tasks are ordered by dependency. Full task list generated by `/speckit.tasks`.

**Story 1 sequence** (core — UI + API + worker):
1. Expand `setting_service.py` (ALLOWED_KEYS, DEFAULTS, validation) + tests
2. Update `openapi.json` (PATCH bump) + regenerate TS client
3. Add `httpx` to worker, add `API_URL` config, update `compose.yaml`
4. Rewrite `agent_runner.py` to fetch settings via API + update agent.py workaround + tests
5. Implement `AgentSettings.tsx` component + update settings page

**Story 2** (provider switching): Covered by Story 1 implementation — no separate code needed beyond validation.

**Story 3** (temperature validation): Backend validation in Story 1 step 1; frontend validation in Story 1 step 5.

### quickstart.md

See [quickstart.md](./quickstart.md) for developer setup steps.
