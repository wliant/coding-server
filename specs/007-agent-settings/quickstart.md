# Developer Quickstart: Agent Settings Configuration (007)

## Prerequisites

- Docker + Docker Compose installed
- Python 3.12 in PATH (for OpenAPI regeneration)
- Node.js 20 + npm in PATH

## Local Dev Setup

```bash
# Start all services
task dev

# Verify settings page works
open http://localhost:3000/settings
```

## Running Tests

```bash
# API tests (inside container)
docker compose -f compose.yaml -f compose.dev.yaml exec api pytest tests/

# Worker tests (inside container)
docker compose -f compose.yaml -f compose.dev.yaml exec worker pytest tests/

# Agent library tests
cd agents/simple_crewai_pair_agent
python -m pytest tests/unit/

# E2E tests
task e2e
```

## After Modifying openapi.json

```bash
# Regenerate TypeScript client
cd web && npm run generate
```

## Key Files for This Feature

| File | Purpose |
|---|---|
| `api/src/api/services/setting_service.py` | Add new keys + validation |
| `worker/src/worker/config.py` | Remove LLM fields, add API_URL |
| `worker/src/worker/agent_runner.py` | Fetch settings via httpx |
| `agents/.../agent.py` | Fix OPENAI_API_KEY workaround |
| `web/src/components/settings/AgentSettings.tsx` | New UI component |
| `web/src/app/settings/page.tsx` | Add Agent Settings tab |
| `openapi.json` | PATCH version bump |
| `compose.yaml` | Remove LLM env vars from worker, add API_URL |

## New Setting Keys

After this feature, `GET /settings` returns all 7 keys:

```json
{
  "settings": {
    "agent.work.path": "",
    "agent.simple_crewai.llm_provider": "ollama",
    "agent.simple_crewai.llm_model": "qwen2.5-coder:7b",
    "agent.simple_crewai.llm_temperature": "0.2",
    "agent.simple_crewai.ollama_base_url": "http://localhost:11434",
    "agent.simple_crewai.openai_api_key": "",
    "agent.simple_crewai.anthropic_api_key": ""
  }
}
```
