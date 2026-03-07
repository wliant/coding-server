# Data Model: Agent Settings Configuration (007)

## Existing Table: `settings`

No new table or migration is required. All agent settings are stored in the existing `settings` key/value table.

```
settings
├── key          TEXT (PK, max 100 chars)   — namespaced setting key
├── value        TEXT NOT NULL              — setting value, stored as plain text string
└── updated_at   TIMESTAMPTZ NOT NULL       — last updated timestamp
```

## New Setting Keys

| Key | Type (logical) | Validation | Default |
|-----|---------------|------------|---------|
| `agent.simple_crewai.llm_provider` | enum string | must be one of: `ollama`, `openai`, `anthropic` | `"ollama"` |
| `agent.simple_crewai.llm_model` | string | non-empty string | `"qwen2.5-coder:7b"` |
| `agent.simple_crewai.llm_temperature` | decimal string | parseable as float, in range [0.0, 2.0] | `"0.2"` |
| `agent.simple_crewai.ollama_base_url` | URL string | non-empty string | `"http://localhost:11434"` |
| `agent.simple_crewai.openai_api_key` | string | no validation (may be empty) | `""` |
| `agent.simple_crewai.anthropic_api_key` | string | no validation (may be empty) | `""` |

## Existing Key (unchanged)

| Key | Default |
|-----|---------|
| `agent.work.path` | `""` |

## Full ALLOWED_KEYS set (post-feature)

```python
ALLOWED_KEYS: set[str] = {
    "agent.work.path",
    "agent.simple_crewai.llm_provider",
    "agent.simple_crewai.llm_model",
    "agent.simple_crewai.llm_temperature",
    "agent.simple_crewai.ollama_base_url",
    "agent.simple_crewai.openai_api_key",
    "agent.simple_crewai.anthropic_api_key",
}

DEFAULTS: dict[str, str] = {
    "agent.work.path": "",
    "agent.simple_crewai.llm_provider": "ollama",
    "agent.simple_crewai.llm_model": "qwen2.5-coder:7b",
    "agent.simple_crewai.llm_temperature": "0.2",
    "agent.simple_crewai.ollama_base_url": "http://localhost:11434",
    "agent.simple_crewai.openai_api_key": "",
    "agent.simple_crewai.anthropic_api_key": "",
}
```

## Validation Rules (applied in `upsert_settings`)

1. **Unknown key**: HTTP 422 — existing behaviour, unchanged.
2. **`agent.simple_crewai.llm_provider`**: HTTP 422 if value not in `{"ollama", "openai", "anthropic"}`.
3. **`agent.simple_crewai.llm_temperature`**: HTTP 422 if value cannot be parsed as float, or parsed float is outside [0.0, 2.0].
4. All other string keys: no additional validation beyond known-key check.

## Worker Config Changes

Remove from `worker/src/worker/config.py`:
- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_TEMPERATURE`, `OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

Add to `worker/src/worker/config.py`:
- `API_URL: str = "http://localhost:8000"` — URL of the API service

## CodingAgentConfig Mapping (worker → agent)

At job-execution time the worker:
1. Calls `GET {API_URL}/settings`
2. Maps response to `CodingAgentConfig` fields:

| Settings key | CodingAgentConfig field |
|---|---|
| `agent.simple_crewai.llm_provider` | `llm_provider` |
| `agent.simple_crewai.llm_model` | `llm_model` |
| `agent.simple_crewai.llm_temperature` | `llm_temperature` (cast to float) |
| `agent.simple_crewai.ollama_base_url` | `ollama_base_url` |
| `agent.simple_crewai.openai_api_key` | `openai_api_key` |
| `agent.simple_crewai.anthropic_api_key` | `anthropic_api_key` |
