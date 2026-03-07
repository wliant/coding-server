# Research: Agent Settings Configuration (007)

## Decision 1: Worker HTTP Client Library

**Decision**: Add `httpx[asyncio]` to `worker/pyproject.toml`

**Rationale**: The worker is fully async (FastAPI + asyncpg + asyncio). httpx is the standard async-first HTTP client in the Python ecosystem, already used by FastAPI's test client. It supports async `httpx.AsyncClient` natively. aiohttp is heavier and adds more dependencies.

**Alternatives considered**:
- `aiohttp` — heavier, less ergonomic API, not needed
- `requests` — synchronous only, incompatible with async worker loop
- Direct DB access — violates service boundary (worker must not import from api package per MEMORY.md)

---

## Decision 2: API URL Configuration in Worker

**Decision**: Add `API_URL: str = "http://localhost:8000"` to `worker/src/worker/config.py` and `API_URL: http://api:8000` to the worker service in `compose.yaml`.

**Rationale**: The worker already follows the pattern of configuring service URLs via env vars (`TOOLS_GATEWAY_URL`, `DATABASE_URL`, `REDIS_URL`). Adding `API_URL` is consistent and allows overriding in different environments (dev, test, prod).

**Alternatives considered**:
- Hardcoding `http://api:8000` in the worker — violates configurability pattern
- Deriving from DATABASE_URL — fragile, unrelated config should not be derived from another

---

## Decision 3: Temperature Validation Location

**Decision**: Validate temperature in `api/src/api/services/setting_service.py` (in `upsert_settings`), not in a Pydantic schema field.

**Rationale**: All settings are stored as strings in the key/value table. The service layer already handles key validation (ALLOWED_KEYS check). Adding type-specific validation there is consistent. A separate Pydantic model per setting key would over-engineer what is intentionally a simple generic store.

**Alternatives considered**:
- Separate typed endpoint `/settings/agent` — adds endpoint complexity, breaks existing client pattern
- Pydantic validator per key — requires moving away from generic dict schema, breaking client compatibility

---

## Decision 4: LLM Provider Validation

**Decision**: Validate `agent.simple_crewai.llm_provider` against the set `{"ollama", "openai", "anthropic"}` in `upsert_settings`.

**Rationale**: The agent library only supports these three. Storing an invalid provider would silently fail at job-execution time, making debugging difficult.

**Alternatives considered**:
- Validate only at agent-run time — defers error too late; user would not know until a job fails

---

## Decision 5: API Key Masking Strategy

**Decision**: The frontend always displays `••••••••` (fixed placeholder) for API key fields when the stored value is non-empty. The API returns the actual value but the frontend never renders it. When saving, if the user leaves the field as the placeholder (or empty), the frontend sends an empty string to clear the key.

**Rationale**: Simplest approach that prevents credential exposure. The frontend can check if `initialValue !== ""` to decide whether to show placeholder. No server-side masking needed.

**Alternatives considered**:
- Server-side masking (return `***` from API) — complicates round-trip: frontend can't distinguish "was a value saved" from "save cleared it"
- Show full value — exposes credentials in UI

---

## Decision 6: compose.yaml LLM Env Var Removal

**Decision**: Remove `LLM_PROVIDER`, `LLM_MODEL`, `OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` (no `LLM_TEMPERATURE`) from the worker service in `compose.yaml`. The worker's `config.py` LLM fields are also removed.

**Rationale**: Feature explicitly requires "strictly from configuration only — no env var fallback."

Note: `LLM_TEMPERATURE` is also missing from compose.yaml (it was only in config.py defaults). All 6 LLM vars removed from config.py; compose.yaml has 5 (no temperature var listed).

---

## Decision 7: OPENAI_API_KEY Env Var in Agent Library

**Decision**: Change `os.environ.setdefault("OPENAI_API_KEY", config.openai_api_key)` in `agent.py` to `os.environ["OPENAI_API_KEY"] = config.openai_api_key or "PLACEHOLDER"`.

**Rationale**: `setdefault` respects an existing env var, meaning a system-level `OPENAI_API_KEY` env var could override the configured value. Always overwriting from config ensures the configured value is authoritative. Using `"PLACEHOLDER"` when the value is empty satisfies CrewAI's import-time non-empty check.

**Alternatives considered**:
- Remove the workaround — CrewAI raises an error at import time if OPENAI_API_KEY is absent/empty, so this cannot be removed without a CrewAI patch
- Use `setdefault` as-is — allows env var to override config, violating spec requirement

---

## Decision 8: OpenAPI Spec Update

**Decision**: Update `openapi.json` `info.version` with a PATCH bump and add a description to the settings endpoint documenting valid keys. No schema shape change needed.

**Rationale**: The endpoint schema (`dict[str, str]`) is unchanged. However, the set of valid keys expanded — this is a non-breaking additive change. A PATCH version bump + description update satisfies Constitution Principle VI without requiring a generated client regeneration.
