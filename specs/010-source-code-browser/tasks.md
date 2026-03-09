# Tasks: Source Code Browser in Task Detail

**Input**: Design documents from `/specs/010-source-code-browser/`
**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/worker-files-api.yaml ✅

**Tests**: Included — Constitution Principle II (TDD) is NON-NEGOTIABLE. Worker route tests are written before implementation. E2e test is written before final validation.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this belongs to (US1 / US2 / US3)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Environment & Dependencies)

**Purpose**: Env vars and package installation — can be done before any implementation.

- [ ] T001 Add `CORS_ORIGINS: "http://localhost:3000"` to worker service env in `compose.dev.yaml`
- [ ] T002 [P] Add `NEXT_PUBLIC_WORKER_URL: "http://localhost:8001"` to web service env in `compose.dev.yaml`
- [ ] T003 [P] Add `react-syntax-highlighter` and `@types/react-syntax-highlighter` to dependencies in `web/package.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core changes that MUST be complete before any user story UI work can begin.

**⚠️ CRITICAL**: No user story implementation can start until this phase is complete.

- [ ] T004 Add `assigned_worker_url: str | None = None` field to `TaskDetailResponse` in `api/src/api/schemas/task.py`
- [ ] T005 Update `openapi.json` — add `assigned_worker_url` as nullable string property to the `TaskDetailResponse` schema object (alongside existing `assigned_worker_id`)
- [ ] T006 Regenerate TypeScript client by running `npm run generate` inside `web/` (depends on T005)
- [ ] T007 [P] Add `CORSMiddleware` import and registration to `agents/simple_crewai_pair_agent/src/worker/app.py` — read origins from `CORS_ORIGINS` env var (default `http://localhost:3000`), matching the pattern in `api/src/api/main.py`
- [ ] T008 [P] Create `web/src/lib/workerClient.ts` — export types `FileEntry`, `FileListResponse`, `FileContentResponse` (matching `contracts/worker-files-api.yaml`), and functions `getWorkerBaseUrl(assignedWorkerUrl)`, `fetchFileTree(baseUrl)`, `fetchFileContent(baseUrl, path)`

**Checkpoint**: Foundation ready — run `docker compose exec api pytest tests/` and verify no regressions before proceeding.

---

## Phase 3: User Story 1 — Browse Generated Source Files (Priority: P1) 🎯 MVP

**Goal**: A completed or failed task shows a Source Code section below the task detail panel with a file tree and inline code viewer. Auto-selects README.md (or first file) on load.

**Independent Test**: Complete a task in the dev environment, navigate to `/tasks/{id}`, confirm the Source Code section renders with a file tree, and clicking a file shows syntax-highlighted content.

### Tests for User Story 1 (TDD — write first, confirm they FAIL before implementing T011–T012)

- [ ] T009 [P] [US1] Write worker file-listing tests in `agents/simple_crewai_pair_agent/tests/test_routes_files.py`: `test_list_files_returns_sorted_flat_list`, `test_list_files_includes_root_field`, `test_list_files_404_when_no_work_dir_state`, `test_list_files_empty_dir_returns_empty_entries`
- [ ] T010 [P] [US1] Write worker file-content tests in `agents/simple_crewai_pair_agent/tests/test_routes_files.py`: `test_get_file_content_text_file`, `test_get_file_content_binary_file_returns_empty_content`, `test_get_file_content_truncates_large_file`, `test_get_file_content_403_path_traversal`, `test_get_file_content_404_file_missing`, `test_get_file_content_400_when_path_is_directory`, `test_get_file_content_404_when_no_work_dir_state`

### Implementation for User Story 1

- [ ] T011 [US1] Implement `GET /files` route in `agents/simple_crewai_pair_agent/src/worker/routes.py` — add `FileEntry`, `FileListResponse` Pydantic models; return 404 if `_state.work_dir_path` is None or dir missing; walk directory recursively; detect binary (null bytes in first 8 KB); sort entries by path ascending; return `FileListResponse`
- [ ] T012 [US1] Implement `GET /files/{path:path}` route in `agents/simple_crewai_pair_agent/src/worker/routes.py` — add `FileContentResponse` Pydantic model; 404 if no work dir state; resolve full path, 403 if outside work dir; 404 if not found; 400 if directory; binary detection; truncate at 500 KB with warning prefix
- [ ] T013 [P] [US1] Create `web/src/components/tasks/FileViewer.tsx` — props: `content`, `path`, `isBinary`, `isLoading`, `error`; use `react-syntax-highlighter` with `highlight.js` renderer; infer language from file extension; render binary placeholder if `isBinary`; render loading skeleton; render inline error message
- [ ] T014 [P] [US1] Create `web/src/components/tasks/FileTree.tsx` — props: `entries: FileEntry[]`, `selectedPath: string | null`, `onSelect: (path: string) => void`; build tree hierarchy from flat list; render directories before files within each level; highlight selected file; directories expand/collapse on click (all top-level entries visible by default)
- [ ] T015 [US1] Create `web/src/components/tasks/SourceCodeSection.tsx` — props: `taskId`, `workerUrl`; on mount call `fetchFileTree`; auto-select `README.md` at root (case-insensitive) or first file entry; call `fetchFileContent` for selected file; render side-by-side layout (`FileTree` left ~240 px, `FileViewer` right flex-grow); show error message if `workerUrl` is null or fetch fails
- [ ] T016 [US1] Update `web/src/app/tasks/[id]/page.tsx` — import `SourceCodeSection`; render `<SourceCodeSection taskId={task.id} workerUrl={task.assigned_worker_url} />` below the main detail panel when `task.status === "completed" || task.status === "failed"`

**Checkpoint**: Run worker tests (`docker compose exec worker pytest tests/test_routes_files.py -v`). Start `task dev`, complete a test task, verify Source Code section renders with file tree and content viewer.

---

## Phase 4: User Story 2 — Download Code from Source Code Section (Priority: P2)

**Goal**: The "Download Code" button lives exclusively in the Source Code section and calls the worker directly. The button is absent from the main task detail panel.

**Independent Test**: With a completed task open, confirm "Download Code" is visible in the Source Code section and clicking it downloads a zip. Confirm the button is NOT present in the main task detail panel.

### Implementation for User Story 2

- [ ] T017 [US2] Add "Download Code" button to `web/src/components/tasks/SourceCodeSection.tsx` — place in the section header alongside the "Source Code" title; call `{getWorkerBaseUrl(workerUrl)}/download` directly (same blob-download pattern as the existing button in `page.tsx`); show loading/error states
- [ ] T018 [US2] Remove the "Download Code" button block (and its `isDownloading` / `downloadError` state) from `web/src/app/tasks/[id]/page.tsx`

**Checkpoint**: Verify "Download Code" button triggers zip download from Source Code section AND is no longer in the main panel (acceptance scenario US2-3 from spec).

---

## Phase 5: User Story 3 — Navigate Large File Trees (Priority: P3)

**Goal**: Directories are expandable/collapsible nodes; nested sub-directories start collapsed by default.

**Independent Test**: With a task that produced nested directories, open the Source Code section, verify directories render as expandable nodes, click to expand a nested directory, verify children appear, click again to collapse.

### Implementation for User Story 3

- [ ] T019 [US3] Update `web/src/components/tasks/FileTree.tsx` — add per-directory expand/collapse state (`Map<string, boolean>`); top-level directories default to expanded, nested directories (depth > 1) default to collapsed; render chevron icon toggle per directory; clicking chevron or directory name toggles expand state without triggering file selection

**Checkpoint**: Open a task with nested directories; confirm root-level dirs are expanded and nested dirs are collapsed; toggle correctly with clicks.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Tests, linting, and final verification across all user stories.

- [ ] T020 [P] Write Playwright e2e test in `web/tests/source-code-browser.spec.ts` — assert: Source Code section visible for completed task; file tree has entries; clicking a file renders content; "Download Code" in section; "Download Code" NOT in main panel; section absent for `in_progress` task
- [ ] T021 Run `task e2e` and verify all acceptance scenarios pass
- [ ] T022 [P] Run Python linter: `cd agents/simple_crewai_pair_agent && ruff check src/` — fix any issues in `routes.py` and `app.py`
- [ ] T023 [P] Run TypeScript type-check: `cd web && npx tsc --noEmit` — fix any type errors in new components and `workerClient.ts`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; T001–T003 are all independent
- **Foundational (Phase 2)**: Depends on Phase 1 completion (T003 needed before T008 types are finalisable); T004–T008 otherwise independent of each other (T006 depends on T005)
- **User Stories (Phase 3–5)**: ALL depend on Phase 2 completion
  - US1 (Phase 3) must complete before US2 and US3 (they extend US1 components)
  - US2 and US3 are otherwise independent of each other
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependency on US2/US3 — **start here**
- **US2 (P2)**: After US1 — adds Download button to `SourceCodeSection.tsx` created in US1
- **US3 (P3)**: After US1 — extends `FileTree.tsx` created in US1; independent of US2

### Within User Story 1

```
T009, T010 (tests) → MUST FAIL before →
T011, T012 (worker routes, parallel) → run worker tests green →
T013, T014 (UI components, parallel) → T015 (SourceCodeSection) → T016 (page.tsx)
```

### Parallel Opportunities

- **Phase 1**: T001, T002, T003 all in parallel
- **Phase 2**: T004 → T005 → T006 sequential; T007 and T008 parallel to each other and to T004
- **Phase 3 tests**: T009 and T010 in parallel
- **Phase 3 impl**: T011 and T012 in parallel; T013 and T014 in parallel; T015 after T013 + T014; T016 after T015
- **Phase 6**: T020, T022, T023 all in parallel; T021 after T020

---

## Parallel Example: User Story 1

```bash
# Step 1 — Write failing tests (together):
T009: test_routes_files.py — file listing tests
T010: test_routes_files.py — file content tests

# Step 2 — Implement worker routes (together, once tests fail confirmed):
T011: routes.py — GET /files
T012: routes.py — GET /files/{path:path}

# Step 3 — Build UI components (together, once worker is green):
T013: FileViewer.tsx
T014: FileTree.tsx

# Step 4 — Wire together:
T015: SourceCodeSection.tsx (needs T013 + T014)
T016: page.tsx (needs T015)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only — ~13 tasks)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T008)
3. Complete Phase 3: US1 (T009–T016)
4. **STOP and VALIDATE**: Source Code section live, file tree + viewer working
5. Demo / ship as MVP

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 complete → File browser live (MVP!)
3. US2 complete → Download button relocated → better UX
4. US3 complete → Collapsible tree → polished navigation
5. Polish phase → E2e coverage + linting clean

### Suggested Scope per Session

| Session | Tasks | Deliverable |
|---------|-------|-------------|
| 1 | T001–T008 | All infra + worker CORS + API schema + TS client |
| 2 | T009–T012 | Worker file endpoints (TDD green) |
| 3 | T013–T016 | Full file browser UI live |
| 4 | T017–T019 | Download relocated + collapsible tree |
| 5 | T020–T023 | E2e + linting clean |

---

## Notes

- [P] tasks operate on different files — safe to run in parallel
- [Story] label maps each task to its user story for traceability
- Constitution Principle II (TDD): T009–T010 MUST be written and confirmed failing BEFORE T011–T012 are implemented
- Run `docker compose exec worker pytest tests/test_routes_files.py -v` after T010 (expect failures) and after T012 (expect all green)
- No new database migrations required for this feature
- The existing `/tasks/{id}/download` endpoint in the main API is NOT removed — the web simply stops calling it
- `task.assigned_worker_url` will be `null` for pre-010 completed tasks; `SourceCodeSection` must handle this gracefully with an error message
