# Data Model: Source Code Browser

**Feature**: 010-source-code-browser
**Date**: 2026-03-09

---

## New Entities (Worker API — in-memory / file system)

### FileEntry

Represents a single node in the working directory (file or directory).

| Field      | Type                    | Nullable | Notes |
|------------|-------------------------|----------|-------|
| `name`     | string                  | No       | Filename or directory name (last path segment) |
| `path`     | string                  | No       | Relative path from working directory root (forward-slash separated) |
| `type`     | `"file" \| "directory"` | No       | Node kind |
| `size`     | integer (bytes)         | Yes      | Files only; `null` for directories |
| `is_binary`| boolean                 | Yes      | Files only; `true` if file contains null bytes in first 8 KB |

**Validation rules**:
- `path` must not contain `..` components; resolved path must be a child of the working directory root.
- `name` is derived from `path` (last segment); not independently user-supplied.
- `size` is the stat-reported byte count at listing time.

**Sorting**: entries are returned sorted by `path` ascending (depth-first, alphabetical within each directory level).

---

### FileListResponse

Wrapper for the file listing endpoint response.

| Field     | Type              | Notes |
|-----------|-------------------|-------|
| `entries` | `FileEntry[]`     | Flat sorted list; client builds tree hierarchy |
| `root`    | string            | Task ID (working directory basename) — aids client-side verification |

---

### FileContentResponse

Content of a single file.

| Field       | Type    | Nullable | Notes |
|-------------|---------|----------|-------|
| `path`      | string  | No       | Relative path (echoed from request) |
| `content`   | string  | No       | UTF-8 decoded file content; empty string if `is_binary` is true |
| `size`      | integer | No       | File size in bytes |
| `is_binary` | boolean | No       | `true` if file detected as binary |

**Truncation rule**: files larger than 500 KB are served with `content` containing only the first 500 KB and a warning prefix: `[TRUNCATED — file exceeds 500 KB. Use Download to access the full file.]\n\n`.

---

## Modified Entities (Main API)

### TaskDetailResponse (extended)

The existing `TaskDetailResponse` schema gains one new field:

| Field                 | Type           | Nullable | Notes |
|-----------------------|----------------|----------|-------|
| `assigned_worker_url` | string         | Yes      | Internal Docker URL of the assigned worker; `null` if no worker assigned or task pre-dates feature 010 |

**No other fields changed.** The main API job model already has `assigned_worker_url` in the DB; this change only surfaces it in the HTTP response schema.

---

## State Transitions Relevant to File Browsing

```
pending → in_progress → completed ──► [Source Code section visible]
                       → failed    ──► [Source Code section visible]
                       → cleaning_up ► [Source Code section NOT visible]
                       → cleaned    ► [Source Code section NOT visible]
```

Worker file endpoints (`GET /files`, `GET /files/{path}`) respond:
- `200 OK` when `_state.work_dir_path` is set and the directory exists.
- `404 Not Found` when `_state.work_dir_path` is `None` (worker restarted without completed-state restoration, or worker was freed).

---

## No New Database Tables

This feature uses only:
- The existing `jobs` table (`assigned_worker_url` column already present).
- The worker's in-memory `_state` object for file serving.
- The file system (working directory on disk).

No migrations required.
