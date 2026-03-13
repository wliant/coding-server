# Source Code Browser
Last updated: 2026-03-13

## Overview

After a coding agent completes (or fails) a task, the user can browse the generated source code directly in the web UI. The browser calls the worker service directly (not through the API proxy) to list files, view content, see diffs, and download archives. The data flow is: `browser → worker (via assigned_worker_url) → filesystem`.

## Domain Concepts

### File Listing

- Recursive listing of all files and directories in the task's working directory
- Respects `.gitignore` patterns — ignored files are excluded from listing
- Returns a tree structure with directories and files as nodes
- Files include name, relative path, type (file/directory), and size

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

### Zip Download

- `GET /download` returns the entire working directory as a zip archive
- Excludes `.git` directory from the archive
- Browser initiates download directly from worker URL

### Path Traversal Protection

All file operations validate that the resolved path stays within the working directory. Requests for paths that resolve outside (e.g., `../../etc/passwd`) are rejected with 403.

## API Contracts

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

### SourceCodeSection (`web/src/components/tasks/SourceCodeSection.tsx`)

Container component rendered on the task detail page when status is `completed` or `failed`. Contains the file tree, file viewer, diff viewer, and download button.

### FileTree (`web/src/components/tasks/FileTree.tsx`)

- Renders the recursive file structure as an expandable/collapsible tree
- Directories are expandable nodes, files are leaf nodes
- Clicking a file loads its content in the FileViewer
- On initial load: auto-selects README.md if present, otherwise the first file in the tree

### FileViewer (`web/src/components/tasks/FileViewer.tsx`)

- Displays file content with syntax highlighting (via `react-syntax-highlighter`)
- Shows placeholder for binary files
- Shows truncation warning for large files
- Language detection based on file extension

### DiffViewer

- Tab or view showing changed files and their diffs
- Individual file diffs with additions/deletions highlighted

### Download Button

- "Download Code" button within the Source Code section
- Calls worker's `/download` endpoint directly
- Moved here from the main task detail panel (no longer appears in task metadata area)

## Configuration

- `CORS_ORIGINS`: Comma-separated allowed origins on each worker (dev: `http://localhost:3000`)
- `NEXT_PUBLIC_WORKER_URL`: Fallback worker URL for the frontend (used when `assigned_worker_url` is not available on pre-010 tasks)

## Cross-Context Dependencies

- **Task Lifecycle**: Source Code section renders only for `completed`/`failed` tasks; uses `assigned_worker_url` from task record
- **Agent Execution**: File/diff/download endpoints are part of the shared worker API
- **Git Integration**: Diff endpoints rely on git history in the working directory
