# Implementation Plan: CrewAI Coding Agent Module

**Branch**: `004-crewai-coding-agent` | **Date**: 2026-03-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-crewai-coding-agent/spec.md`

---

## Summary

Add a standalone Python module `simple_crewai_coding_agent/` to the monorepo. The module uses CrewAI with a two-agent sequential crew (Coder + Reviewer) to generate Python source code from a natural-language requirement. The LLM defaults to Ollama (`qwen2.5-coder:7b`) and is fully configurable via environment variables. Package management uses `uv` with the `uv_build` backend. The module ships with a pytest suite that includes unit tests (no LLM), integration tests (mocked LLM), and a smoke test (real Ollama, run manually).

---

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: `crewai[litellm]>=0.100.0`, `python-dotenv>=1.0.0`
**Storage**: None — output written as plain `.py` files to a caller-specified directory
**Testing**: pytest 8+, pytest-asyncio, pytest-mock; 3-layer strategy (unit / integration / smoke)
**Target Platform**: Local developer machine (Linux / macOS / Windows via WSL)
**Project Type**: Python library with optional CLI entry point
**Performance Goals**: Produce code output in under 60 seconds per run on a machine with Ollama running locally (not a CI/latency target)
**Constraints**: No internet required for default Ollama mode; no UI or API changes
**Scale/Scope**: Single-user local tool; no concurrency requirements

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked post-design below.*

| Principle | Status | Notes |
|---|---|---|
| I. Simplicity-First | ✅ PASS | Minimal 2-agent crew, sequential process, no over-engineering. `pydantic-settings` skipped (only 4 env vars, factory function is sufficient). |
| II. TDD (NON-NEGOTIABLE) | ✅ PASS | Tests defined first per user stories. Unit tests for wiring, integration tests for `kickoff()`, smoke test for end-to-end. Red-Green-Refactor cycle enforced in tasks. |
| III. Modularity | ✅ PASS | Single-purpose package. No cross-module dependencies on `api/`, `worker/`, `tools/`. Public interface documented in `contracts/python-api.md`. |
| IV. Observability | ✅ PASS | Structured logging via Python `logging` module required at INFO level for crew start/completion and at ERROR for LLM failures. |
| V. Incremental Delivery | ✅ PASS | 3 user stories are independently testable and implementable. P1 (core agent) can be delivered without P2 (config) or P3 (tests). |
| VI. API-First with OpenAPI | ✅ PASS (N/A) | This module is a Python library — no REST API. Constitution VI is not applicable. Exception documented in Complexity Tracking table below. |

**Post-design re-check**: All gates still pass. No design decisions introduce additional violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/004-crewai-coding-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── python-api.md    # Python public API contract
└── tasks.md             # Phase 2 output (/speckit.tasks — not created by /speckit.plan)
```

### Source Code (repository root)

```text
simple_crewai_coding_agent/
├── .env.example                                # LLM config template
├── .python-version                             # "3.12"
├── pyproject.toml                              # uv + uv_build, dependencies, pytest config
├── src/
│   └── simple_crewai_coding_agent/
│       ├── __init__.py                         # re-exports run_crew, CrewRunResult
│       ├── config.py                           # make_llm() factory — reads env vars
│       ├── agents.py                           # CoderAgent, ReviewerAgent factories
│       ├── tasks.py                            # CodingTask, ReviewTask factories
│       ├── crew.py                             # CodingCrew class — assembles + runs crew
│       └── main.py                             # CLI entry point (__main__.py or argparse)
└── tests/
    ├── conftest.py                             # shared fixtures (tmp_dir, mock_llm_response)
    ├── unit/
    │   ├── test_config.py                      # make_llm() env var handling
    │   ├── test_agents.py                      # agent attribute assertions (no LLM)
    │   ├── test_tasks.py                       # task wiring assertions
    │   └── test_crew_structure.py              # crew has 2 agents, 2 tasks, sequential
    └── integration/
        ├── test_crew_kickoff.py                # crew.kickoff() with mocked LLM.call
        └── test_smoke.py                       # @pytest.mark.smoke — real Ollama required
```

**Structure Decision**: Single project (Option 1). Follows the `src/` layout convention used by all other monorepo services. Top-level directory is `simple_crewai_coding_agent/` at the repo root, not nested under an existing service.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Constitution VI (OpenAPI) not applicable | Module is a Python library, not a REST API. Generating an OpenAPI spec for a function call has no value and adds maintenance overhead. | Writing an OpenAPI spec for a non-HTTP interface would violate Principle I (Simplicity-First) — the simpler correct approach is `contracts/python-api.md`. |
| uv_build backend (differs from other services) | User explicitly requested `uv` for this module. uv_build is uv's native backend. | Using setuptools would contradict the explicit user requirement. The deviation is isolated — this module has no build-time cross-dependencies with api/worker/tools. |

---

## Implementation Sequence (by User Story)

### Story 1 (P1): Core Coding Agent — `run_crew()` produces code on disk

**TDD Sequence**:
1. Write failing tests: `test_crew_structure.py` (crew has 2 agents, sequential process), `test_agents.py` (role/goal attributes), `test_tasks.py` (context chain)
2. Write failing integration test: `test_crew_kickoff.py` (mocked LLM → output file written)
3. Implement `config.py`, `agents.py`, `tasks.py`, `crew.py`, `__init__.py`
4. Make tests green. Refactor.

**Key implementation notes**:
- `CoderAgent` sets `output_file` on `CodingTask` to `{working_directory}/{project_name}.py`
- `run_crew()` calls `working_directory.mkdir(parents=True, exist_ok=True)` before kickoff
- `make_llm()` is called once and shared across both agents
- Structured log emitted at INFO on crew start and completion; ERROR on exception

### Story 2 (P2): Configurable LLM — env var override works

**TDD Sequence**:
1. Write failing test: `test_config.py` — patch env vars, assert `make_llm()` returns correct model string for each provider
2. Write failing test: assert invalid `LLM_PROVIDER` raises `ValueError` with descriptive message
3. Implement `make_llm()` in `config.py` with `ollama`, `openai`, `anthropic` branches
4. Make tests green.

### Story 3 (P3): Pytest Smoke Test — end-to-end coding task

**TDD Sequence**:
1. Write `test_smoke.py` marked `@pytest.mark.smoke` with a simple coding requirement ("write a function that adds two numbers")
2. Assert: output file exists, is non-empty, contains `def ` (basic Python syntax check)
3. No implementation needed beyond what Story 1 provides — this test exercises the real stack

---

## Key Design Decisions

1. **`CodingTask.output_file`**: CrewAI writes the task output string directly to disk via this parameter. This is the simplest way to get a file on disk without manually parsing `CrewOutput`.

2. **Shared LLM instance**: Both agents receive the same `LLM` object. This ensures a single configuration point and eliminates divergence risk.

3. **`allow_code_execution=False`**: The Coder agent generates code as text — it does not execute it. This avoids Docker/subprocess dependencies for sandboxed execution, keeping the module lightweight.

4. **`CrewRunResult` dataclass**: Wraps `CrewOutput` in a stable, typed structure. Tests assert on `result.code` and `result.review` rather than parsing raw `CrewOutput` internals, insulating the test suite from CrewAI version changes.

5. **No `compose.yaml` entry**: This module does not run as a long-lived service. It is invoked on demand. No Docker Compose integration is required (out of scope for this feature).
