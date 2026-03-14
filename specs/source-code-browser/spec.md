# Source Code Browser
Last updated: 2026-03-14

## Overview

The user can browse source code for tasks in any active state (pending, in_progress, completed, failed) directly in the web UI. For completed/failed tasks with a worker, the browser calls the worker service directly. For pending tasks with a `git_url`, the API proxies file requests via a temporary shallow clone. For in-progress tasks, the API proxies to the sandbox or worker. The data flow depends on task state and available sources.

## Domain Concepts

### File Listing

- Recursive listing of all files and directories in the task's working directory
- Respects `.gitignore` patterns — ignored files are excluded from listing
- Returns a tree structure with directories and files as nodes
- Files include name, relative path, type (file/directory), and size

### File Source Routing

File browsing is available for all active task states. The source of files depends on the task's status and allocated resources:

| Task Status | File Source | Condition |
|-------------|-----------|-----------|
| `pending` | Git repository (temp clone) | Task has `git_url` |
| `in_progress` | Sandbox workspace (live) | Sandbox allocated |
| `in_progress` | Worker workspace | Worker assigned, no sandbox |
| `completed`/`failed` | Worker workspace | Current behavior |
| `cleaning_up`/`cleaned` | Not available | |

### Binary Detection

Files are checked for binary content. Binary files:
- Appear in the file tree but cannot be viewed as text
- Display placeholder: "Binary file — use Download to access"
- Detection uses content sniffing (null byte detection)

### File Content

- Text files are served with their raw content
- Files larger than 500 KB are truncated with a warning prefix
- Syntax highlighting is applied client-side based on file extension

### Diff Viewer

- Shows a list of changed files (via `git diff`)
- Individual file diffs available with before/after content
- Useful for reviewing what the agent actually changed vs. the cloned base
- Diff tab is hidden for new projects (`task_type=scaffold_project` or no `git_url`) — diffs are meaningless without a base commit

### Zip Download

- `GET /download` returns the entire working directory as a zip archive
- Excludes `.git` directory from the archive
- Browser initiates download directly from worker URL

### Path Traversal Protection

All file operations validate that the resolved path stays within the working directory. Requests for paths that resolve outside (e.g., `../../etc/passwd`) are rejected with 403.

## API Contracts

### Worker Endpoints (direct browser access)

All endpoints are on the worker service (not the main API).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/files` | Recursive file listing of working directory |
| GET | `/files/{path:path}` | Read file content by relative path |
| GET | `/diff` | List of changed files |
| GET | `/diff/{path:path}` | Diff content for a specific file |
| GET | `/download` | Download working directory as zip archive |

### GET /files Response

```json
{
  "files": [
    {
      "name": "src",
      "path": "src",
      "type": "directory",
      "children": [
        {
          "name": "main.py",
          "path": "src/main.py",
          "type": "file",
          "size": 1234
        }
      ]
    },
    {
      "name": "README.md",
      "path": "README.md",
      "type": "file",
      "size": 456
    }
  ]
}
```

### GET /files/{path} Response

```json
{
  "path": "src/main.py",
  "content": "import os\n...",
  "size": 1234,
  "is_binary": false,
  "truncated": false
}
```

Binary files return `is_binary: true` with no content. Files over 500 KB return `truncated: true` with partial content.

### API File Proxy Endpoints (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks/{id}/files` | List files for any task (routes to appropriate source) |
| GET | `/tasks/{id}/files/{path}` | Read file content for any task |

Routing logic: `sandbox_url` -> sandbox, `worker_url` -> worker, `git_url` + pending -> temp clone.

### Temp Clone Management

- Shallow clone (`--depth 1`) to `/tmp/task-browse/{task_id}`
- Cached per task — reused across requests for the same pending task
- TTL: 1800 seconds (30 minutes)
- Cleaned up on task status transition (e.g., pending -> in_progress)

## Service Architecture

The source code browser has no dedicated service. It uses endpoints exposed by each worker service:

```
Browser (Next.js client-side)
    │
    ├── GET assigned_worker_url from task detail API
    │   (rewrite container hostname to localhost for browser access)
    │
    └── Direct HTTP calls to worker
        ├── GET /files
        ├── GET /files/{path}
        ├── GET /diff
        ├── GET /diff/{path}
        └── GET /download
```

### Worker URL Resolution

The frontend resolves the worker URL from the task record's `assigned_worker_url` field:
1. Task detail API returns `assigned_worker_url` (e.g., `http://simple_crewai_pair_agent:8001`)
2. `workerClient.ts` rewrites the container hostname to `localhost` (e.g., `http://localhost:8001`)
3. All file browsing requests go directly to the worker, bypassing the main API

This supports multiple workers on different ports — the correct worker is identified per-task.

### CORS

Each worker includes `CORSMiddleware` since the browser calls it directly (cross-origin from `localhost:3000` to `localhost:8001/8004/8005`). The `CORS_ORIGINS` environment variable configures allowed origins.

## UI Components

### Tabbed Layout

The task detail page uses a tabbed layout (Radix UI Tabs) with three tabs:

- **Details** tab: task metadata, status, requirement, actions (Push, Clean Up)
- **Files** tab: file navigator with filter + tree + viewer (uses API proxy endpoints)
- **Diff** tab: diff viewer (uses worker endpoints directly)

Tab visibility:
- Files tab shown when: `git_url || assigned_worker_url || assigned_sandbox_url`
- Diff tab shown when: `!isNewProject && (completed || failed)`

Contextual banners:
- For pending tasks: "Showing repository contents (read-only)"
- For in_progress tasks: "Files may change as the agent works"

### FileNavigatorTab

Container component for the Files tab. Contains:
- Filter input for case-insensitive path filtering
- FileTree component
- FileViewer component
- Uses API proxy endpoints (`/tasks/{id}/files`) instead of direct worker calls

### FileTree (`web/src/components/tasks/FileTree.tsx`)

- Renders the recursive file structure as an expandable/collapsible tree
- Directories are expandable nodes, files are leaf nodes
- Clicking a file loads its content in the FileViewer
- On initial load: auto-selects README.md if present, otherwise the first file in the tree
- Accepts `filter` prop for case-insensitive path filtering with ancestor directory preservation (matching files keep their parent directories visible)

### FileViewer (`web/src/components/tasks/FileViewer.tsx`)

- Displays file content with syntax highlighting (via `react-syntax-highlighter`)
- Shows placeholder for binary files
- Shows truncation warning for large files
- Language detection based on file extension

### DiffTab

- Contains diff viewer showing changed files and their diffs
- Individual file diffs with additions/deletions highlighted
- Uses worker endpoints directly (not API proxy)

### Download Button

- "Download Code" button within the task detail area
- Calls worker's `/download` endpoint directly

## Configuration

- `CORS_ORIGINS`: Comma-separated allowed origins on each worker (dev: `http://localhost:3000`)
- `NEXT_PUBLIC_WORKER_URL`: Fallback worker URL for the frontend (used when `assigned_worker_url` is not available on pre-010 tasks)
- `TEMP_CLONE_DIR`: Directory for temporary clones (default: `/tmp/task-browse`)
- `TEMP_CLONE_TTL_SECONDS`: TTL for cached temp clones (default: `1800`)

## Cross-Context Dependencies

- **Task Lifecycle**: File browsing available for `pending`, `in_progress`, `completed`, `failed` tasks; uses `assigned_worker_url`, `assigned_sandbox_url`, and `git_url` from task record
- **Agent Execution**: File/diff/download endpoints are part of the shared worker API
- **Git Integration**: Diff endpoints rely on git history in the working directory; temp clone uses git_url for pending tasks
- **Platform Infrastructure**: API file proxy service routes requests to sandbox, worker, or temp clone based on task state
