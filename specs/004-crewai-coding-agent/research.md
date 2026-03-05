# Research: CrewAI Coding Agent Module

**Phase**: Phase 0 — Outline & Research
**Feature**: 004-crewai-coding-agent
**Date**: 2026-03-04

---

## Decision 1: CrewAI Crew Composition

**Decision**: Two-agent, sequential crew — **Coder** agent followed by **Reviewer** agent.

**Rationale**: Sequential process (`Process.sequential`) is deterministic, easy to debug, and appropriate for a write-then-review pipeline. The Reviewer task receives the Coder output automatically via CrewAI's `context` parameter — no manual output passing required. Two specialised agents create testable seams and match the spec's FR-002 requirement exactly.

**Alternatives considered**:
- `Process.hierarchical` — adds a manager LLM that dynamically delegates; unnecessary overhead for two fixed-role agents; triples LLM cost per run.
- Single agent with two tasks — loses role specialisation; harder to extend and test independently.
- `Flow` (event-driven) — designed for complex branching; too heavy for a linear pipeline.

---

## Decision 2: LLM Backend — Ollama via LiteLLM

**Decision**: Use `crewai.LLM(model="ollama/<model>", base_url=...)` with `crewai[litellm]` extra. Default model: `qwen2.5-coder:7b` (lightweight) or `qwen2.5-coder:32b` (high quality).

**Rationale**: CrewAI routes non-native providers through LiteLLM. The `ollama/<name>` prefix is the LiteLLM convention. The `LLM` object must be passed explicitly to each agent — relying on env vars alone is unreliable because CrewAI's internal paths default to OpenAI when no `llm=` argument is present. `qwen2.5-coder:7b` matches the Aider benchmark performance of GPT-3.5-class models and is pullable by most developer machines.

**Workaround required**: CrewAI validates the presence of `OPENAI_API_KEY` at import time even for non-OpenAI providers. Setting `OPENAI_API_KEY=NA` (a literal dummy value) silences this check without side effects. This is a documented community workaround.

**Alternatives considered**:
- `langchain_community.chat_models.ChatOllama` — works but adds LangChain as a dependency; CrewAI's native `LLM` class is preferred.
- `deepseek-coder-v2` — strong alternative; same configuration pattern.
- `codellama` — older; superseded by qwen2.5-coder for coding tasks.

---

## Decision 3: LLM Configurability Pattern

**Decision**: Hybrid pattern — env vars define the provider/model/URL; a `make_llm()` factory function reads them and constructs the `LLM` object explicitly. No configuration file required on disk.

**Env vars**:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | Backend provider: `ollama`, `openai`, `anthropic` |
| `LLM_MODEL` | `qwen2.5-coder:7b` | Model name (without provider prefix) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature (low = deterministic) |
| `OPENAI_API_KEY` | `NA` | Dummy value to silence CrewAI validation when not using OpenAI |

**Rationale**: Env vars enable configuration without touching source code (satisfies FR-006). The factory function provides a typed, testable seam — tests can call `make_llm()` with overridden env vars or mock it entirely. This is simpler than a config file and avoids secrets on disk.

**Alternatives considered**:
- Constructor argument only (`CodingCrew(llm=...)`) — ergonomic but requires the caller to construct the LLM object, pushing boilerplate to users.
- `pydantic-settings` BaseSettings — adds a dependency for a module with minimal config; over-engineered for 4 env vars.

---

## Decision 4: Package Manager — uv with `uv_build` Backend

**Decision**: Use `uv` as the package manager with `uv_build` as the build backend, `src/` layout. This deviates from the other monorepo services (which use setuptools) because the user explicitly requested `uv`.

**Rationale**: `uv` is 10–100x faster than pip for dependency resolution and lockfile generation. `uv_build` is uv's native build backend (analogous to hatchling). The `src/` layout is the same convention used by all other monorepo services (`api/`, `worker/`, `tools/`), ensuring consistency in code organisation even if the build backend differs.

**pyproject.toml build-system block**:
```toml
[build-system]
requires = ["uv_build>=0.10.7,<0.11.0"]
build-backend = "uv_build"
```

**Deviation note**: Other modules in the monorepo use `setuptools`. This module intentionally uses `uv_build` per the feature requirement. This is a standalone module with no cross-module build integration, so the deviation has zero impact on the existing build pipeline.

**Alternatives considered**:
- `setuptools` — matches existing services; user explicitly requested `uv`.
- `hatchling` — popular alternative to uv_build; slightly more config; no meaningful advantage here.

---

## Decision 5: Testing Strategy — Three Layers

**Decision**: Three test layers under `tests/`:

| Layer | Dir | Requires LLM? | CI? | Purpose |
|---|---|---|---|---|
| Unit | `tests/unit/` | No | Yes | Test agent/task wiring, crew structure, config factory |
| Integration | `tests/integration/` | Mocked | Yes | Test `crew.kickoff()` with intercepted LLM HTTP calls |
| Smoke | `tests/smoke/` | Real Ollama | No (manual) | End-to-end coding task validation |

**Rationale**: LLM output is non-deterministic — asserting exact strings tests the mock, not the agent behaviour. Unit tests validate structural wiring (correct agents, task context chains, config loading) without any LLM. Integration tests use `unittest.mock.patch` on `crewai.LLM.call` to intercept and replay canned responses, covering the `crew.kickoff()` path in CI. Smoke tests (marked `@pytest.mark.smoke`) require a live Ollama instance and are explicitly out of scope for automated execution per the feature spec.

**Alternatives considered**:
- VCR cassettes (`pytest-recording`) — records real HTTP traffic and replays; excellent but requires an initial real Ollama run to generate cassettes; adds `vcrpy` dependency; mock approach is simpler for two-agent crews.
- `crew.test()` method — built into CrewAI for iterative evaluation; useful for tuning but not for CI assertions.

---

## Decision 6: No OpenAPI Contract (Constitution VI Exception)

**Decision**: This module does not expose a REST API. Constitution Principle VI (API-First with OpenAPI) does not apply. The public interface is a Python function — documented in `contracts/python-api.md`.

**Rationale**: The module is a Python library invoked programmatically. Its contract is the function signature and return type, not an HTTP endpoint. Generating an OpenAPI spec for a non-HTTP interface would violate Constitution Principle I (Simplicity-First).

**Exception documented in**: `plan.md` Complexity Tracking table.

---

## Resolved Unknowns

| Unknown | Resolution |
|---|---|
| Recommended Ollama model for coding | `qwen2.5-coder:7b` (default), `qwen2.5-coder:32b` (high quality) |
| How to pass Ollama to CrewAI | `crewai.LLM(model="ollama/<name>", base_url=...)` + `crewai[litellm]` |
| OPENAI_API_KEY validation issue | Set `OPENAI_API_KEY=NA` as documented workaround |
| Build backend for uv | `uv_build` (uv's native backend) |
| How to test without real Ollama | `unittest.mock.patch("crewai.llm.LLM.call", ...)` |
| Module location in monorepo | New top-level directory `simple_crewai_coding_agent/` alongside existing services |
