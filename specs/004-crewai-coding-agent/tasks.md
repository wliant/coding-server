# Tasks: CrewAI Coding Agent Module

**Input**: Design documents from `/specs/004-crewai-coding-agent/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: Included — spec explicitly requests pytest suite with TDD approach (Constitution Principle II: NON-NEGOTIABLE).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3)
- Exact file paths are relative to `simple_crewai_coding_agent/` unless noted

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create the module directory, package manifest, and tooling configuration from scratch.

- [x] T001 Create top-level module directory `simple_crewai_coding_agent/` with subdirectory layout: `src/simple_crewai_coding_agent/`, `tests/unit/`, `tests/integration/`
- [x] T002 Create `simple_crewai_coding_agent/pyproject.toml` with `uv_build` backend, `crewai[litellm]>=0.100.0`, `python-dotenv>=1.0.0`, dev extras (`pytest>=8.0`, `pytest-asyncio>=0.23`, `pytest-mock>=3.12`, `ruff>=0.4`), pytest config (`asyncio_mode="auto"`, `testpaths=["tests"]`, markers for `smoke`), and ruff config (`src=["src"]`, `line-length=100`)
- [x] T003 [P] Create `simple_crewai_coding_agent/.python-version` containing `3.12`
- [x] T004 [P] Create `simple_crewai_coding_agent/.env.example` documenting all five env vars: `LLM_PROVIDER=ollama`, `LLM_MODEL=qwen2.5-coder:7b`, `OLLAMA_BASE_URL=http://localhost:11434`, `LLM_TEMPERATURE=0.2`, `OPENAI_API_KEY=NA`
- [x] T005 Run `uv sync` inside `simple_crewai_coding_agent/` to generate `uv.lock` and verify the venv is created successfully

**Checkpoint**: `uv sync` completes without errors; `uv run pytest --collect-only` exits cleanly (zero tests collected is acceptable)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types and shared test infrastructure that every user story depends on. Must be complete before any user story work begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T006 Create `src/simple_crewai_coding_agent/result.py` defining the `CrewRunResult` dataclass with fields `code: str`, `review: str`, `output_file: Path` — this is the stable public return type per `contracts/python-api.md`
- [x] T007 Create stub `src/simple_crewai_coding_agent/config.py` with `make_llm() -> crewai.LLM` that returns an Ollama LLM using the five env vars from `.env.example` with defaults hardcoded as fallback (no provider branching yet — single `ollama` path only)
- [x] T008 Create `tests/conftest.py` with two shared fixtures: `tmp_working_dir` (a `pytest tmp_path`-based `Path` fixture) and `mock_llm_call` (a `mocker.patch` on `crewai.llm.LLM.call` returning a canned `MagicMock` with `.content = "def placeholder(): pass"`)
- [x] T009 [P] Create `tests/unit/__init__.py` and `tests/integration/__init__.py` (empty, makes pytest discover them as packages)

**Checkpoint**: `uv run pytest --collect-only` collects `tests/` without import errors; `from simple_crewai_coding_agent.result import CrewRunResult` works

---

## Phase 3: User Story 1 — Run Coding Agent on a Task (Priority: P1) 🎯 MVP

**Goal**: `run_crew(working_directory, project_name, requirement)` executes a two-agent sequential CrewAI crew, writes generated code to `{working_directory}/{project_name}.py`, and returns a `CrewRunResult`.

**Independent Test**: Run `uv run pytest tests/unit/ tests/integration/test_crew_kickoff.py -m "not smoke"` — all tests pass with mocked LLM, output file is written to `tmp_working_dir`.

### Tests for User Story 1 ⚠️ Write First — Confirm FAIL Before Implementing

- [x] T010 [US1] Write failing unit tests in `tests/unit/test_crew_structure.py`: assert `build_crew(tmp_dir, "proj", "req")` returns a `Crew` with exactly 2 agents, `Process.sequential`, and 2 tasks; assert `crew.tasks[1].context` contains `crew.tasks[0]`
- [x] T011 [P] [US1] Write failing unit tests in `tests/unit/test_agents.py`: assert `CoderAgent` has `role="Senior Python Developer"`, `allow_code_execution=False`, `max_retry_limit=3`; assert `ReviewerAgent` has `role="Code Reviewer"`
- [x] T012 [P] [US1] Write failing unit tests in `tests/unit/test_tasks.py`: assert `CodingTask` `output_file` equals `str(working_directory / "proj.py")`; assert `ReviewTask.context` contains `CodingTask`; assert `CodingTask.description` contains `{requirement}` placeholder
- [x] T013 [US1] Write failing integration test in `tests/integration/test_crew_kickoff.py`: using `mock_llm_call` fixture, call `run_crew(tmp_working_dir, "calculator", "write an add function")`, assert `result.output_file` exists on disk, is non-empty, and `result.code` is a non-empty string; assert `result.review` is a non-empty string

### Implementation for User Story 1

- [x] T014 [P] [US1] Implement `CoderAgent` and `ReviewerAgent` factory functions in `src/simple_crewai_coding_agent/agents.py` — each accepts an `llm: crewai.LLM` argument and returns a configured `crewai.Agent` with the attributes asserted in T011
- [x] T015 [P] [US1] Implement `CodingTask` and `ReviewTask` factory functions in `src/simple_crewai_coding_agent/tasks.py` — `coding_task(agent, working_directory, project_name)` sets `output_file`; `review_task(agent, coding_task)` sets `context=[coding_task]`
- [x] T016 [US1] Implement `CodingCrew` class in `src/simple_crewai_coding_agent/crew.py` with `__init__(self, working_directory, project_name, requirement)` that calls `make_llm()`, builds agents/tasks, assembles `crewai.Crew(process=Process.sequential)`; add `run() -> CrewRunResult` method that calls `crew.kickoff()`, reads the written file, and returns `CrewRunResult`
- [x] T017 [US1] Implement `run_crew()` public entry point in `src/simple_crewai_coding_agent/__init__.py` — validates inputs (`ValueError` on empty strings), calls `working_directory.mkdir(parents=True, exist_ok=True)`, instantiates `CodingCrew`, calls `run()`, returns `CrewRunResult`; re-export `CrewRunResult` from `result.py`
- [x] T018 [US1] Add structured logging to `src/simple_crewai_coding_agent/crew.py`: `logger.info("crew starting", ...)` before `kickoff()`, `logger.info("crew completed", ...)` after, `logger.error("crew failed", ...)` in exception handler with `raise RuntimeError(...)` wrapping the original exception
- [x] T019 [US1] Run `uv run pytest tests/unit/ tests/integration/test_crew_kickoff.py -m "not smoke" -v` — confirm all T010–T013 tests now pass; fix any failures before proceeding

**Checkpoint**: All US1 tests pass. `run_crew(Path("/tmp/test"), "hello", "write a hello function")` can be called in a Python REPL with mocked LLM and returns a `CrewRunResult` with a non-empty `code` field.

---

## Phase 4: User Story 2 — Configure LLM Provider (Priority: P2)

**Goal**: `make_llm()` reads `LLM_PROVIDER` env var and returns a correctly configured `crewai.LLM` for `ollama`, `openai`, and `anthropic`. Unknown providers raise `ValueError` with a descriptive message. No source code change required to switch providers.

**Independent Test**: Run `uv run pytest tests/unit/test_config.py -v` — all provider-switching tests pass without any real LLM connection.

### Tests for User Story 2 ⚠️ Write First — Confirm FAIL Before Implementing

- [x] T020 [US2] Write failing unit tests in `tests/unit/test_config.py`:
  - Patch env `LLM_PROVIDER=ollama` → assert `make_llm().model` starts with `"ollama/"` and `base_url` equals `OLLAMA_BASE_URL` default
  - Patch env `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini` → assert `make_llm().model == "gpt-4o-mini"` (no prefix)
  - Patch env `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-haiku-4-5-20251001` → assert `make_llm().model` starts with `"anthropic/"`
  - Patch env `LLM_PROVIDER=unknown` → assert `make_llm()` raises `ValueError` with message containing `"unknown"`
  - No `LLM_PROVIDER` set → assert defaults to `ollama` with `qwen2.5-coder:7b`

### Implementation for User Story 2

- [x] T021 [US2] Expand `src/simple_crewai_coding_agent/config.py`: replace the stub `make_llm()` with the full factory — `if provider == "ollama": LLM(model=f"ollama/{model}", base_url=base_url, temperature=temperature)`, `elif provider == "openai": LLM(model=model, ...)`, `elif provider == "anthropic": LLM(model=f"anthropic/{model}", ...)`, `else: raise ValueError(f"Unknown LLM provider: {provider!r}. Supported: ollama, openai, anthropic")`; set `os.environ.setdefault("OPENAI_API_KEY", "NA")` at the top of the `ollama` branch
- [x] T022 [US2] Run `uv run pytest tests/unit/test_config.py -v` — confirm all T020 tests pass; fix any failures before proceeding

**Checkpoint**: Setting `LLM_PROVIDER=openai LLM_MODEL=gpt-4o-mini` in the shell and importing `make_llm()` returns an `LLM` with `model="gpt-4o-mini"`. All US1 tests still pass (run full `uv run pytest tests/unit/ tests/integration/test_crew_kickoff.py -m "not smoke"` to confirm no regression).

---

## Phase 5: User Story 3 — Automated Test Validates Agent Behaviour (Priority: P3)

**Goal**: A `@pytest.mark.smoke` test exists in `tests/integration/test_smoke.py` that exercises a real end-to-end coding task when invoked manually against a live Ollama instance. The test is defined and runnable; it is NOT executed in CI.

**Independent Test**: `uv run pytest tests/integration/test_smoke.py --collect-only` shows one smoke test collected. A developer with Ollama running can execute `uv run pytest tests/integration/test_smoke.py -m smoke -v` and the test passes.

- [x] T023 [US3] Write smoke test `tests/integration/test_smoke.py` marked `@pytest.mark.smoke`: call `run_crew(tmp_working_dir, "adder", "Write a Python function named add that takes two numbers and returns their sum")`, assert `result.output_file.exists()`, assert `result.output_file.stat().st_size > 0`, assert `"def " in result.code` (basic Python syntax presence check); add a module-level docstring explaining this test requires a running Ollama instance
- [x] T024 [US3] Verify `smoke` marker is declared in `pyproject.toml` under `[tool.pytest.ini_options] markers` so pytest does not emit `PytestUnknownMarkWarning`; run `uv run pytest tests/integration/test_smoke.py --collect-only` and confirm the test is collected without warnings

**Checkpoint**: `uv run pytest -m "not smoke"` runs the full non-smoke suite and all tests pass. `uv run pytest tests/integration/test_smoke.py --collect-only` shows one test collected.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: CLI entry point, lint compliance, and quickstart validation.

- [x] T025 [P] Create `src/simple_crewai_coding_agent/__main__.py` with an `argparse` CLI that accepts `--working-dir`, `--project-name`, `--requirement` arguments, calls `run_crew()`, and prints the output file path and review to stdout — enables `uv run python -m simple_crewai_coding_agent ...` invocation as documented in `quickstart.md`
- [x] T026 [P] Run `uv run ruff check src/ tests/` and `uv run ruff format --check src/ tests/` — fix all reported issues until both commands exit with code 0
- [x] T027 Perform a manual dry-run of `quickstart.md` steps from a clean shell (no `.env`, only `.env.example`): verify `uv sync`, `cp .env.example .env`, and `uv run pytest -m "not smoke"` all succeed as documented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 complete — **blocks all user story phases**
- **User Story Phases (3, 4, 5)**: All depend on Phase 2 complete; can then be worked sequentially in priority order
- **Polish (Phase 6)**: Depends on Phase 3 + Phase 4 + Phase 5 complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Phase 2 (Foundational). No dependency on US2 or US3.
- **US2 (P2)**: Depends on Phase 2. No dependency on US1 — `config.py` stub exists from Phase 2. Does integrate with US1's `CodingCrew` (T022), but US1 unit tests continue to pass because they mock `make_llm()`.
- **US3 (P3)**: Depends on US1 complete (requires `run_crew()` to exist). Can be written alongside US2.

### Within Each User Story

- Tests MUST be written and confirmed FAIL before any implementation begins (Red phase)
- Factories (`agents.py`, `tasks.py`) before the `CodingCrew` assembler (`crew.py`)
- `CodingCrew` before `run_crew()` public entry point
- Each story: run full test suite at checkpoint to confirm no regressions

### Parallel Opportunities

- T003, T004 (Phase 1): parallel — different files
- T009 (Phase 2): parallel with T006, T007, T008
- T011, T012 (Phase 3 tests): parallel — different test files
- T014, T015 (Phase 3 implementation): parallel — `agents.py` and `tasks.py` are independent files
- T025, T026 (Phase 6): parallel — `__main__.py` and ruff lint are independent

---

## Parallel Example: User Story 1

```bash
# Step 1 — write all US1 tests simultaneously (different files, no deps):
T010: tests/unit/test_crew_structure.py
T011: tests/unit/test_agents.py       ← parallel with T010
T012: tests/unit/test_tasks.py        ← parallel with T010
# T013 depends on conftest fixtures (T008) — write after confirming conftest is ready

# Step 2 — implement agents and tasks simultaneously:
T014: src/simple_crewai_coding_agent/agents.py   ← parallel with T015
T015: src/simple_crewai_coding_agent/tasks.py    ← parallel with T014

# Step 3 — sequential (deps):
T016: src/simple_crewai_coding_agent/crew.py     (needs T014 + T015)
T017: src/simple_crewai_coding_agent/__init__.py  (needs T016)
T018: logging in crew.py                          (extends T016)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T005)
2. Complete Phase 2: Foundational (T006–T009) — **critical gate**
3. Complete Phase 3: US1 tests first (T010–T013 must FAIL), then implementation (T014–T018), then verify (T019)
4. **STOP and VALIDATE**: `uv run pytest tests/unit/ tests/integration/test_crew_kickoff.py -m "not smoke" -v` — all green
5. Demo: call `run_crew()` in a Python REPL with mocked LLM

### Incremental Delivery

1. Setup + Foundational → module skeleton ready
2. US1 complete → `run_crew()` works (MVP — core value delivered)
3. US2 complete → LLM is fully configurable without code changes
4. US3 complete → smoke test written for human validation
5. Polish → CLI, lint, quickstart verified

---

## Notes

- All paths are relative to `simple_crewai_coding_agent/` (repo root sibling directory)
- `[P]` = can run in parallel with other `[P]` tasks in the same phase
- TDD is NON-NEGOTIABLE (Constitution II): write test → confirm FAIL → implement → confirm PASS
- Smoke tests (`@pytest.mark.smoke`) are excluded from all automated runs; only run manually with Ollama
- Run `uv run pytest -m "not smoke"` (not `pytest`) to use the virtual environment managed by uv
- Commit after each phase checkpoint and after each user story verification
