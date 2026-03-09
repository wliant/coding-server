# Implementation Plan: Source Code Browser in Task Detail

**Branch**: `010-source-code-browser` | **Date**: 2026-03-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-source-code-browser/spec.md`

## Summary

Add a "Source Code" section to the Task Detail page (visible for `completed` and `failed` tasks) that renders a GitHub-style file tree and inline code viewer. The viewer calls two new worker API endpoints (`GET /files` and `GET /files/{path}`) directly from the browser. The "Download Code" button moves into this section and also calls the worker directly. Requires: CORS on the worker, two new worker routes, exposing `assigned_worker_url` in the task API response, updating `openapi.json`, and adding `react-syntax-highlighter` to the web app.

## Technical Context

**Language/Version**: Python 3.12 (worker, api) · TypeScript / Node.js 20 (web)
**Primary Dependencies**: FastAPI 0.115+ (worker, api) · Next.js 15 / React 19 / shadcn/ui / @hey-api/client-fetch (web) · react-syntax-highlighter (new, web)
**Storage**: PostgreSQL 16 (main API) · worker in-memory state + filesystem (worker file serving)
**Testing**: pytest + pytest-asyncio (worker, api) · Playwright (web e2e)
**Target Platform**: Docker Compose dev · Linux containers
**Performance Goals**: File tree renders in < 2 s for 200-file directories; file content loads in < 1 s for files ≤ 100 KB (SC-002, SC-003)
**Constraints**: Files > 500 KB truncated with warning; binary files not rendered as text
**Scale/Scope**: Single worker, single task at a time; up to 200 files per working directory

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity-First | ✅ Pass | Flat file list over nested tree; hand-written fetch wrapper instead of generated client (2 endpoints); no new DB tables |
| II. TDD (NON-NEGOTIABLE) | ✅ Pass | Worker endpoint tests written before routes; component tests before UI implementation |
| III. Modularity & SRP | ✅ Pass | SourceCodeSection / FileTree / FileViewer are independent components; worker routes are self-contained |
| IV. Observability | ✅ Pass | Worker file endpoints emit structured logs on errors (file not found, path traversal attempt) |
| V. Incremental Delivery | ✅ Pass | P1 (file browser), P2 (download relocation), P3 (tree navigation) are independently deliverable |
| VI. API-First with OpenAPI (NON-NEGOTIABLE) | ⚠️ Exception | Worker file API contract defined in `contracts/worker-files-api.yaml` before implementation. TypeScript client is hand-written (see Complexity Tracking). Main API `openapi.json` updated before frontend work begins. |

**Constitution Check: PASS** (one documented exception — see Complexity Tracking)

## Project Structure

### Documentation (this feature)

```text
specs/010-source-code-browser/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── worker-files-api.yaml   # OpenAPI contract for new worker endpoints
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code Changes

```text
# Worker — new endpoints + CORS
agents/simple_crewai_pair_agent/
├── src/worker/
│   ├── routes.py          # ADD: GET /files, GET /files/{path:path}, CORS-aware router
│   └── app.py             # ADD: CORSMiddleware
└── tests/
    └── test_routes_files.py   # NEW: unit tests for file listing + content endpoints

# Main API — expose assigned_worker_url in task response
api/src/api/
├── schemas/task.py        # ADD: assigned_worker_url field to TaskDetailResponse
└── routes/tasks.py        # No logic change; field propagates via from_attributes

openapi.json               # UPDATE: add assigned_worker_url to TaskDetailResponse schema

# Web — new Source Code section components + updated Task Detail page
web/
├── package.json           # ADD: react-syntax-highlighter + @types/react-syntax-highlighter
├── src/
│   ├── client/            # REGENERATE: npm run generate (picks up new API field)
│   ├── lib/
│   │   └── workerClient.ts       # NEW: fetchFileTree(), fetchFileContent() hand-written fetch wrappers
│   ├── components/tasks/
│   │   ├── SourceCodeSection.tsx  # NEW: top-level section (file tree + viewer + download)
│   │   ├── FileTree.tsx           # NEW: recursive tree navigation panel
│   │   └── FileViewer.tsx         # NEW: syntax-highlighted code + binary/truncation states
│   └── app/tasks/[id]/
│       └── page.tsx               # MODIFY: add SourceCodeSection; remove Download button from main panel
└── tests/
    └── source-code-browser.spec.ts  # NEW: Playwright e2e test

# Compose — env vars for worker CORS + web NEXT_PUBLIC_WORKER_URL
compose.dev.yaml            # ADD: CORS_ORIGINS to worker env; NEXT_PUBLIC_WORKER_URL to web env
```

**Structure Decision**: Follows existing project conventions — new components under `web/src/components/tasks/`, new worker routes added to the existing `routes.py` via the existing `make_router()` pattern, new worker tests in the existing `tests/` directory alongside `test_routes.py`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle VI exception: hand-written worker fetch client instead of generated TS | Only 2 new worker endpoints (`/files`, `/files/{path}`); the entire client is ~40 lines | Setting up a full generation pipeline (export worker OpenAPI, Taskfile command, `web/src/worker-client/` dir) adds more scaffolding than the feature warrants for 2 trivial endpoints |

## Implementation Phases

### Phase 1 — Worker API (P1 backend, prerequisite for all UI work)

**Goal**: New file listing and content endpoints on the worker; CORS enabled.

**Tasks**:
1. Write `tests/test_routes_files.py`:
   - `test_list_files_returns_flat_list` — mock `_state.work_dir_path` with a temp dir; assert entries sorted by path; assert root field
   - `test_list_files_404_when_no_state` — `_state.work_dir_path = None`; assert 404
   - `test_get_file_content_text` — small text file; assert content, size, is_binary=False
   - `test_get_file_content_binary` — file with null bytes; assert is_binary=True, content=""
   - `test_get_file_content_truncated` — file > 500 KB; assert content starts with truncation warning
   - `test_get_file_content_path_traversal` — path `../../etc/passwd`; assert 403
   - `test_get_file_content_404_file_missing` — valid state but nonexistent path; assert 404
   - `test_get_file_content_400_directory` — path points to a directory; assert 400
2. Implement `GET /files` in `routes.py`:
   - Guard: return 404 if `_state.work_dir_path` is None or directory doesn't exist
   - Walk directory recursively; build `FileEntry` per node; sort by path; return `FileListResponse`
   - Binary detection: read first 8 KB, check for null bytes
3. Implement `GET /files/{path:path}` in `routes.py`:
   - Guard: 404 if no working directory; resolve full path; 403 if outside work dir; 404 if missing; 400 if directory
   - Binary detection: same null-byte check; if binary return `is_binary=True`, `content=""`
   - Truncation: if `size > 500 * 1024`, prepend warning line and truncate at 500 KB
4. Add `CORSMiddleware` to `app.py` — origins from `CORS_ORIGINS` env var (default `http://localhost:3000`)
5. Add `CORS_ORIGINS=http://localhost:3000` to worker env in `compose.dev.yaml`
6. Run worker tests: `docker compose exec worker pytest tests/test_routes_files.py -v`

---

### Phase 2 — Main API Schema Update (prerequisite for web generated client)

**Goal**: Expose `assigned_worker_url` in the task detail response.

**Tasks**:
1. Add `assigned_worker_url: str | None = None` to `TaskDetailResponse` in `api/src/api/schemas/task.py`
2. Update `openapi.json` — add `assigned_worker_url` field (nullable string) to the `TaskDetailResponse` schema object
3. Run main API tests: `docker compose exec api pytest tests/ -v`
4. Regenerate TypeScript client: `cd web && npm run generate`

---

### Phase 3 — Web Worker Client & Dependencies (prerequisite for UI components)

**Goal**: `workerClient.ts` helper and `react-syntax-highlighter` installed.

**Tasks**:
1. Add `react-syntax-highlighter` and `@types/react-syntax-highlighter` to `web/package.json`
2. Create `web/src/lib/workerClient.ts`:
   - Export `getWorkerBaseUrl(assignedWorkerUrl: string | null | undefined): string` — returns `process.env.NEXT_PUBLIC_WORKER_URL ?? assignedWorkerUrl ?? ''`
   - Export `fetchFileTree(workerBaseUrl: string): Promise<FileListResponse>`
   - Export `fetchFileContent(workerBaseUrl: string, path: string): Promise<FileContentResponse>`
   - Export TypeScript types: `FileEntry`, `FileListResponse`, `FileContentResponse` (matching `contracts/worker-files-api.yaml` schemas)
3. Add `NEXT_PUBLIC_WORKER_URL=http://localhost:8001` to web env in `compose.dev.yaml`

---

### Phase 4 — UI Components (P1 user story: browse source files)

**Goal**: Source Code section with file tree and code viewer.

**Tasks**:
1. Create `FileViewer.tsx`:
   - Props: `content: string`, `path: string`, `isBinary: boolean`, `isLoading: boolean`, `error: string | null`
   - Loading state: skeleton or spinner
   - Binary state: grey placeholder message
   - Content state: `<SyntaxHighlighter>` with language inferred from file extension
   - Error state: red inline error message
2. Create `FileTree.tsx`:
   - Props: `entries: FileEntry[]`, `selectedPath: string | null`, `onSelect: (path: string) => void`
   - Builds tree hierarchy from flat `entries` list; renders folders as expandable rows, files as clickable rows
   - Selected file highlighted; folders expand/collapse on click
   - Directories sorted before files within each level (or alphabetical — consistent with `ls`-style ordering)
3. Create `SourceCodeSection.tsx`:
   - Props: `taskId: string`, `workerUrl: string | null | undefined`
   - On mount: call `fetchFileTree`; auto-select README.md or first file; call `fetchFileContent` for selected file
   - Layout: `flex` row — `FileTree` (left, fixed ~240px) + `FileViewer` (right, flex-grow)
   - Header row: "Source Code" heading + "Download Code" button (calls `{workerBaseUrl}/download` directly, same flow as existing download handler)
   - Error state if `workerUrl` is null/unavailable
4. Update `web/src/app/tasks/[id]/page.tsx`:
   - Import `SourceCodeSection`
   - Render `<SourceCodeSection>` below the main panel when `task.status === "completed" || task.status === "failed"`
   - Remove the existing "Download Code" button block from the main panel
   - Pass `task.assigned_worker_url` as `workerUrl` prop

---

### Phase 5 — E2E Test & Validation (P2 + P3 acceptance)

**Goal**: Verify end-to-end behaviour in the running dev environment.

**Tasks**:
1. Write `web/tests/source-code-browser.spec.ts` (Playwright):
   - Navigate to a completed task detail page
   - Assert Source Code section is visible
   - Assert file tree renders at least one entry
   - Click a file; assert code viewer content is non-empty
   - Assert "Download Code" button exists in Source Code section
   - Assert "Download Code" button does NOT exist in main task panel
   - Assert Source Code section is NOT visible for an `in_progress` task
2. Run `task e2e` to verify
3. Verify `task dev` + manual browser test: file tree, click file, download

## Quickstart (see quickstart.md)

See [quickstart.md](./quickstart.md) for local dev setup commands.
