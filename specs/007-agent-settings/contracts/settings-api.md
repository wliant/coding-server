# Contract: Settings API — Agent Settings Keys (007)

**Endpoints**: `GET /settings`, `PUT /settings` (unchanged shape)
**OpenAPI version bump**: PATCH (additive key expansion, no schema change)

## Overview

The `/settings` endpoints are unchanged in shape. This contract documents the expanded set of valid keys introduced by feature 007.

## GET /settings

Returns all settings with defaults for any unset key.

**Response** (unchanged schema):
```json
{
  "settings": {
    "agent.work.path": "/some/path",
    "agent.simple_crewai.llm_provider": "ollama",
    "agent.simple_crewai.llm_model": "qwen2.5-coder:7b",
    "agent.simple_crewai.llm_temperature": "0.2",
    "agent.simple_crewai.ollama_base_url": "http://localhost:11434",
    "agent.simple_crewai.openai_api_key": "",
    "agent.simple_crewai.anthropic_api_key": ""
  }
}
```

Note: API keys are returned as plain text strings. The UI is responsible for masking them.

## PUT /settings

Partial update — only supply keys to change. Unknown keys return 422.

**Request** (partial update example):
```json
{
  "settings": {
    "agent.simple_crewai.llm_provider": "openai",
    "agent.simple_crewai.llm_model": "gpt-4o",
    "agent.simple_crewai.openai_api_key": "sk-abc123"
  }
}
```

**Validation errors** (HTTP 422):

| Condition | Error |
|---|---|
| Key not in ALLOWED_KEYS | `"Unknown setting keys: <key>"` |
| `agent.simple_crewai.llm_provider` not in `{ollama, openai, anthropic}` | `"Invalid llm_provider: must be one of ollama, openai, anthropic"` |
| `agent.simple_crewai.llm_temperature` not parseable as float | `"Invalid llm_temperature: must be a number"` |
| `agent.simple_crewai.llm_temperature` outside [0.0, 2.0] | `"Invalid llm_temperature: must be between 0.0 and 2.0"` |

## Valid Keys Reference (complete post-007 set)

| Key | Valid Values | Default |
|---|---|---|
| `agent.work.path` | any string | `""` |
| `agent.simple_crewai.llm_provider` | `ollama` \| `openai` \| `anthropic` | `"ollama"` |
| `agent.simple_crewai.llm_model` | any non-empty string | `"qwen2.5-coder:7b"` |
| `agent.simple_crewai.llm_temperature` | float string in [0.0, 2.0] | `"0.2"` |
| `agent.simple_crewai.ollama_base_url` | any string | `"http://localhost:11434"` |
| `agent.simple_crewai.openai_api_key` | any string | `""` |
| `agent.simple_crewai.anthropic_api_key` | any string | `""` |
