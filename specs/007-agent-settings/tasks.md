# Tasks: Agent Settings Configuration

**Input**: Design documents from `/specs/007-agent-settings/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/settings-api.md ✅

**Tests**: Included — Constitution Principle II (TDD) is NON-NEGOTIABLE. Test tasks MUST run and FAIL before their corresponding implementation tasks.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Dependencies & Configuration)

**Purpose**: Add httpx dependency and update worker + compose configuration before any story work begins.

- [x] T001 Add `httpx[asyncio]` to dependencies list in `worker/pyproject.toml`
- [x] T002 [P] Remove LLM fields (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_TEMPERATURE`, `OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) from `worker/src/worker/config.py`; add `API_URL: str = "http://localhost:8000"`
- [x] T003 [P] Update worker service in `compose.yaml`: remove LLM env vars (`LLM_PROVIDER`, `LLM_MODEL`, `OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`); add `API_URL: http://api:8000`

**Checkpoint**: Worker deps and config updated. No LLM env vars remain in worker or compose.

---

## Phase 2: Foundational (OpenAPI Contract)

**Purpose**: Update the OpenAPI spec and regenerate the TypeScript client. Blocks all web UI work.

**⚠️ CRITICAL**: T005 must complete before any web component work begins.

- [x] T004 Update `openapi.json`: bump `info.version` by PATCH, add description to `GET /settings` and `PUT /settings` paths documenting the full valid key set (see `contracts/settings-api.md`)
- [x] T005 Regenerate TypeScript client by running `cd web && npm run generate` (depends on T004)

**Checkpoint**: OpenAPI spec updated, TS client current. Web implementation can now proceed.

---

## Phase 3: User Story 1 — Configure Agent LLM Settings in UI (Priority: P1) 🎯 MVP

**Goal**: Operators can view and update all 6 agent LLM settings via a new "Agent Settings" tab. Settings persist in DB and the worker uses them on the next job run.

**Independent Test**: Navigate to Settings → Agent Settings tab, set `llm_provider` to `openai`, model to `gpt-4o`, and save. Call `GET /settings` and verify both keys are persisted. Run a task and confirm the worker constructs `CodingAgentConfig` from the saved settings (not from env vars).

### Tests for User Story 1

> **Write and confirm these tests FAIL before starting T009+**

- [x] T006 [US1] Write failing unit tests for new setting keys (6 keys, defaults, validation) in `api/tests/unit/test_setting_service.py` — cover: all 6 keys accepted, defaults returned when empty, unknown keys rejected (422), `llm_provider` invalid value rejected (422), `llm_temperature` non-numeric rejected (422), `llm_temperature` out-of-range rejected (422)
- [x] T007 [P] [US1] Write failing integration tests for new settings keys in `api/tests/integration/test_settings_api.py` — cover: `GET /settings` returns all 7 keys with defaults; `PUT /settings` with all 6 new keys returns 200; `PUT /settings` with invalid provider returns 422; `PUT /settings` with invalid temperature returns 422
- [x] T008 [US1] Write failing unit tests for updated `agent_runner` in `worker/tests/unit/test_agent_runner.py` — cover: httpx `GET {API_URL}/settings` called before agent run; settings values mapped to `CodingAgentConfig` fields; job marked failed with "unable to fetch agent settings" if httpx raises `httpx.RequestError`; worker no longer receives or uses `settings.LLM_PROVIDER` etc.

### Implementation for User Story 1

- [x] T009 [US1] Expand `ALLOWED_KEYS`, `DEFAULTS`, and `upsert_settings` validation in `api/src/api/services/setting_service.py` — add 6 new keys per `data-model.md`, add provider enum validation, add temperature float+range validation (depends on T006)
- [x] T010 [P] [US1] Fix `OPENAI_API_KEY` env var workaround in `agents/simple_crewai_pair_agent/src/simple_crewai_pair_agent/agent.py`: change `os.environ.setdefault(...)` to `os.environ["OPENAI_API_KEY"] = config.openai_api_key or "PLACEHOLDER"` so config is always authoritative
- [x] T011 [US1] Rewrite `worker/src/worker/agent_runner.py`: use `httpx.AsyncClient` to call `GET {settings.API_URL}/settings` before constructing `CodingAgentConfig`; on `httpx.RequestError` mark job failed with "unable to fetch agent settings"; map response keys to config fields per `data-model.md` (depends on T008, T009)
- [x] T012 [P] [US1] Implement `web/src/components/settings/AgentSettings.tsx`: LLM Provider dropdown (ollama/openai/anthropic), Model text input, Temperature numeric input with [0.0, 2.0] client-side validation, Ollama Base URL text input, OpenAI API Key masked input (show `••••••••` when stored value non-empty), Anthropic API Key masked input (same masking); Save/Cancel buttons matching `GeneralSettings.tsx` pattern (depends on T005)
- [x] T013 [US1] Add "Agent Settings" tab to `web/src/app/settings/page.tsx`: add `TabsTrigger value="agent"` and `TabsContent` rendering `<AgentSettings>` with `initialSettings` and `onSave` props; extend `handleSave` to merge partial updates (depends on T012)

**Checkpoint**: US1 complete. Settings page shows Agent Settings tab; all 6 fields save and reload correctly; worker uses DB settings for agent config; tests pass.

---

## Phase 4: User Story 2 — Switch LLM Provider (Priority: P2)

**Goal**: The provider enum validation and worker routing introduced in Phase 3 correctly handle all three providers (ollama/openai/anthropic) end-to-end.

**Independent Test**: Set provider to `openai` with a model and API key; run a task; verify job error (expected — no real key) references OpenAI, not Ollama.

### Tests for User Story 2

> **Note**: US2 implementation is complete after Phase 3. These tasks add per-provider test coverage.

- [x] T014 [P] [US2] Add per-provider unit tests to `api/tests/unit/test_setting_service.py` — confirm `ollama`, `openai`, and `anthropic` each accepted; `anthropic_api_key` saved and retrieved; verify defaults include all 6 keys regardless of provider
- [x] T015 [P] [US2] Add worker per-provider test to `worker/tests/unit/test_agent_runner.py` — mock `httpx` response with `llm_provider=openai`; assert `CodingAgentConfig.llm_provider == "openai"` and `openai_api_key` passed through; repeat for `anthropic`

**Checkpoint**: US2 verified. Provider switching confirmed end-to-end by tests. US1 tests remain green.

---

## Phase 5: User Story 3 — Validate Temperature Input (Priority: P3)

**Goal**: Invalid temperature values are caught with a clear error message before reaching the backend; valid values persist successfully.

**Independent Test**: In the Agent Settings UI, enter `-1` and click Save; verify error message appears and no network request is made. Enter `abc` and click Save; verify error. Enter `0.5` and click Save; verify success.

### Tests for User Story 3

- [x] T016 [P] [US3] Add frontend input validation tests for `AgentSettings.tsx` — verify that temperatures `"-1"`, `"2.1"`, `"abc"` show validation error messages and do not call `onSave`; verify `"0.5"`, `"0.0"`, `"2.0"` pass validation and call `onSave`
- [x] T017 [P] [US3] Add backend edge-case temperature tests to `api/tests/unit/test_setting_service.py` — cover boundary values: `"0.0"` and `"2.0"` accepted; `"-0.1"` and `"2.001"` rejected; `""` rejected; `"nan"` rejected

**Checkpoint**: US3 verified. Temperature validation confirmed at both frontend and backend layers.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Observability, cleanup, and validation against quickstart.md.

- [x] T018 [P] Ensure no API key values appear in worker logs: audit `worker/src/worker/agent_runner.py` log statements; confirm `openai_api_key` and `anthropic_api_key` fields are never logged
- [x] T019 [P] Update `agents/simple_crewai_pair_agent/tests/unit/test_agent.py` to verify the `OPENAI_API_KEY` env var is set from config (not from environment) after the T010 change
- [x] T020 Run `cd api && ruff check src/` and `cd worker && ruff check src/` — fix any linting errors introduced by feature changes
- [x] T021 Validate against `quickstart.md`: start `task dev`, navigate to Settings → Agent Settings, confirm all 6 fields display with defaults, save a change, reload, and confirm persisted values

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
  └─► Phase 2 (Foundational — OpenAPI/TS client)
        └─► Phase 3 (US1 — Core) ◄─── BLOCKS Phase 4, 5, 6
              ├─► Phase 4 (US2 — Provider switching)
              ├─► Phase 5 (US3 — Temperature validation)
              └─► Phase 6 (Polish)
```

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 1 + Phase 2. No dependency on US2 or US3.
- **US2 (P2)**: Depends on US1 implementation (T009, T011). Can begin immediately after Phase 3 checkpoint.
- **US3 (P3)**: Depends on US1 implementation (T009, T012). Can begin immediately after Phase 3 checkpoint.

### Within Phase 3 (TDD Order)

```
T006 + T007 + T008 (tests — write and FAIL first)
  └─► T009 (API service — makes T006+T007 pass)
  └─► T010 (agent lib — parallel, independent file)
  └─► T011 (worker — makes T008 pass, depends on T009)
  └─► T012 (web component — parallel with T009-T011)
        └─► T013 (settings page — depends on T012)
```

### Parallel Opportunities

- T002 ‖ T003 (both Phase 1, different files)
- T006 ‖ T007 ‖ T008 (all test-write tasks, different test files)
- T010 ‖ T012 (different repos/files, no shared dependency)
- T014 ‖ T015 (Phase 4, different test files)
- T016 ‖ T017 (Phase 5, different test files)
- T018 ‖ T019 ‖ T020 (Phase 6, independent)

---

## Parallel Execution Example: Phase 3

```bash
# Step 1 — Write all failing tests in parallel (different files):
Task A: T006 — api/tests/unit/test_setting_service.py
Task B: T007 — api/tests/integration/test_settings_api.py
Task C: T008 — worker/tests/unit/test_agent_runner.py

# Step 2 — Confirm all tests fail, then implement in parallel:
Task A: T009 — api/src/api/services/setting_service.py
Task B: T010 — agents/.../agent.py
Task C: T012 — web/src/components/settings/AgentSettings.tsx

# Step 3 — Depends on T009 and T012:
Task A: T011 — worker/src/worker/agent_runner.py
Task B: T013 — web/src/app/settings/page.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T005)
3. Complete Phase 3: User Story 1 (T006–T013) — TDD order strictly
4. **STOP and VALIDATE**: `task dev` → Settings → Agent Settings tab works, worker uses DB settings
5. Demo/deploy if ready

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Phase 3 → US1 complete → **MVP** (operators can configure Ollama or switch to OpenAI/Anthropic)
3. Phase 4 → US2 validated (provider switching confirmed by tests)
4. Phase 5 → US3 validated (temperature validation confirmed at both layers)
5. Phase 6 → Polish complete

---

## Notes

- **[P] tasks** = different files, no shared incomplete dependencies — safe to parallelize
- **TDD is non-negotiable**: T006/T007/T008 MUST fail before T009/T011 begin
- **API keys in logs**: Never log `openai_api_key` or `anthropic_api_key` field values (Principle IV)
- **No migration**: The `settings` table already supports arbitrary keys — no Alembic migration needed
- **Commit cadence**: Commit after each logical group (e.g., after Phase 1, after tests written, after each implementation task)
- **Worker test update**: T008 also removes the old `settings` argument (which carried LLM env vars) from `run_coding_agent` signature — update call sites in `worker/src/worker/worker.py`
