# Research: Source Code Browser in Task Detail

**Feature**: 010-source-code-browser
**Date**: 2026-03-09

---

## 1. File Listing API Shape

**Decision**: Return a **flat sorted list** of `FileEntry` objects.

**Rationale**: A flat list is simpler to produce (single recursive walk) and simpler to serialize. The client builds the tree hierarchy from the relative `path` field — this is a trivial O(n) operation done once on load. GitHub's Trees API also uses a flat list for the same reasons. A deeply nested recursive JSON structure is harder to extend (e.g., adding pagination, streaming) and provides no UX benefit.

**Alternatives considered**:
- Recursive nested JSON (`children: [...]`) — more complex to produce, harder to stream/paginate, no client-side benefit.
- Lazy loading per directory (like VS Code's file explorer) — out of scope for MVP; the expected scale (≤200 files per task) doesn't justify the added round-trips.

---

## 2. File Content Endpoint Path Design

**Decision**: `GET /files/{path:path}` — FastAPI's `path` parameter type accepts forward-slashes, making nested file paths natural to express.

**Rationale**: REST-idiomatic; no query-string encoding needed for the UI layer. FastAPI's `path:path` annotation transparently handles URL-encoded slashes. Path traversal protection is applied server-side after resolving the full path.

**Alternatives considered**:
- `GET /files/content?path=src/main.py` — query params work but feel less RESTful for a resource identifier; special characters still need URL encoding.
- Dedicated `POST /files/read` with body — introduces a non-idempotent verb for a read operation; violates REST conventions.

---

## 3. Binary File Detection

**Decision**: Server-side check — read first **8 KB** of file content, return `is_binary: true` if null bytes (`\x00`) are found. Additionally check common binary extensions as a fast-path guard.

**Rationale**: Null-byte detection is the standard heuristic used by `git diff`, `file(1)`, and most text editors. It correctly handles UTF-8 source files while catching compiled artifacts, images, archives, and other binaries. 8 KB is sufficient to detect null bytes in virtually all binary formats without reading large files into memory.

**Alternatives considered**:
- Extension allowlist only (`.py`, `.ts`, `.json`, etc.) — misses unusual extensions; produces false negatives for agent-generated files with novel extensions.
- Using `libmagic` / `python-magic` — adds a native dependency; overkill for this use case.

---

## 4. Browser-Accessible Worker URL

**Decision**: Add `NEXT_PUBLIC_WORKER_URL` env var to the web service. The frontend uses this env var as the base URL for all direct worker calls. Add `assigned_worker_url: str | None` to `TaskDetailResponse` for completeness, but the browser URL is resolved from the env var (overrides the internal Docker URL).

**Rationale**: The worker is registered in the DB with its Docker-internal URL (`http://worker:8001`). Browsers cannot resolve Docker service hostnames. Exposing the browser-accessible URL via an env var (`http://localhost:8001` in dev) is explicit, zero-surprise, and works in both dev and production without requiring DNS tricks or URL transformation logic in the frontend.

**Alternatives considered**:
- Hostname replacement (`internalUrl.replace('worker', 'localhost')`) — brittle; breaks when service names change or in multi-host production deployments.
- Storing a separate "external URL" in the DB — adds schema complexity; not justified for single-worker MVP.
- Next.js API route proxy — defeats the "direct call" design requirement from the spec.

**Dev setup**: Set `NEXT_PUBLIC_WORKER_URL=http://localhost:8001` in `compose.dev.yaml` web env block. Worker port 8001 is already exposed on localhost.

---

## 5. CORS for Direct Browser → Worker Calls

**Decision**: Add `CORSMiddleware` to the worker FastAPI app with origins controlled by a `CORS_ORIGINS` env var (same pattern as the main API). Default in dev: `http://localhost:3000`.

**Rationale**: Browsers enforce CORS. The worker currently has no CORS headers. Without this, the file listing and content calls will be blocked by the browser. Matching the pattern from the main API ensures consistency and keeps config explicit.

**Dev setup**: Add `CORS_ORIGINS=http://localhost:3000` to worker env in `compose.dev.yaml`.

---

## 6. Syntax Highlighting Library

**Decision**: `react-syntax-highlighter` with the `highlight.js` renderer.

**Rationale**: Mature, battle-tested library with React 19 support, tree-shakeable language grammars, broad language coverage (Python, TypeScript, JavaScript, JSON, YAML, Markdown, shell, etc.). Integrates cleanly with Tailwind by accepting `style` prop from `highlight.js` theme presets. Lighter than Monaco Editor (which brings a full IDE runtime) and simpler to bundle than `shiki` (which requires async WASM initialisation incompatible with simple RSC boundaries).

**Alternatives considered**:
- `shiki` / `@shikijs/react` — excellent accuracy, but async-first initialisation adds complexity in client components; larger bundle.
- Monaco Editor — full IDE in the browser; far too heavy for read-only code viewing.
- No syntax highlighting — acceptable fallback, but poor UX for code review.

---

## 7. Constitution Principle VI Exception — Worker Client

**Decision**: Use **hand-written fetch calls** (not a generated TypeScript client) for the two new worker file endpoints.

**Rationale**: Only 2 endpoints are added. Setting up a full generation pipeline (export worker OpenAPI, add `generate-worker` Taskfile command, maintain `web/src/worker-client/`) would add more scaffolding than the feature warrants. The endpoints are simple enough that a thin hand-written `fetchFileTree()` / `fetchFileContent()` wrapper in a `workerClient.ts` file is cleaner and easier to maintain.

**Constitution compliance**: Documented here and in `plan.md` Complexity Tracking as required by Principle VI.

---

## 8. File Tree Initial State

**Decision**: On load, auto-select `README.md` at the root if present; otherwise select the first file (depth-first, alphabetical order) in the flat list.

**Rationale**: Matches GitHub's repository viewer behaviour (confirmed as the UX reference in the spec). Delivers immediate value without an extra click. The file list is available immediately after the listing API call, so pre-selection adds no extra network round-trip.
