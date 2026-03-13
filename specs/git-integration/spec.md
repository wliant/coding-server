# Git Integration
Last updated: 2026-03-13

## Overview

Git operations are central to the task execution flow: cloning repositories before agent execution, and pushing results back to remotes after completion. GitHub token management enables authenticated access to private repositories.

## Domain Concepts

### Clone Flow

When a task has a `git_url`, the worker clones the repository into the working directory before running the agent:

1. Retrieve GitHub token from task settings payload
2. If URL is a `github.com` URL and a token is configured, inject token into the URL
3. Clone the repository into `{WORK_DIR}/{job_id}`
4. If stale working directory exists (from a retried task), clear it first
5. Handle branch:
   - If branch specified and exists remotely → check it out
   - If branch specified but doesn't exist remotely → create from default branch
   - If no branch specified → use default branch

### Push Flow

Push is triggered by the user after a task completes. Two paths exist:

**Worker push (primary)**: `POST /tasks/{id}/push` on the API → proxied to worker's `POST /push`
- Worker creates branch `task/{job_id_prefix}` (first 8 chars of job UUID)
- Force-pushes to the project's git URL
- Uses GitHub token for authentication on `github.com` URLs

**Legacy API-direct push**: `api/src/api/services/git_service.py` — `push_working_directory_to_remote()`
- Used as fallback when worker is not available
- Uses `gitpython` to interact with the repository

### GitHub Token Injection

Token injection applies **only** to `github.com` URLs:

```
Original:  https://github.com/user/repo.git
Injected:  https://{token}@github.com/user/repo.git
```

Non-GitHub URLs use system credentials (SSH keys or other configured auth).

### Branch Naming Convention

Push operations create a branch named `task/{job_id_prefix}` where `job_id_prefix` is the first 8 characters of the job UUID. Example: `task/a1b2c3d4`.

## API Contracts

### POST /tasks/{id}/push

Triggers a push of the completed task's working directory to the remote repository.

```json
// Request: no body required (git_url can optionally be provided if not set on project)

// Response (success)
{"message": "Pushed to remote", "branch": "task/a1b2c3d4"}

// Response (error)
{"detail": "No git URL configured for this project"}
```

The API proxies this request to the worker's `/push` endpoint using `httpx`.

### Worker POST /push

```json
// Request from API
{"git_url": "https://github.com/user/repo.git", "github_token": "ghp_...", "branch": "task/a1b2c3d4"}

// Response
{"message": "Pushed successfully", "branch": "task/a1b2c3d4"}
```

## Service Architecture

### Worker Git Utilities (`agents/*/src/worker/git_utils.py`)

Each worker has identical git utility functions:

- `inject_github_token(url: str, token: str) → str`: Injects token into GitHub URLs
- `clone_repository(git_url: str, target_dir: str, branch: str | None, github_token: str | None)`: Clones with optional token injection and branch handling

### API Git Service (`api/src/api/services/git_service.py`)

- `push_working_directory_to_remote(work_dir, git_url, github_token, branch)`: Legacy direct push using gitpython

### Token Storage

GitHub token is stored in the `settings` table with key `github.token`. It is:
- Fetched by the controller when building the work payload for delegation
- Passed to workers as part of the settings dict in the WorkRequest
- Displayed as masked (`••••••••`) in the Settings UI when a value exists

## UI Components

### PushToRemoteButton

- Appears on the task detail page for `completed` tasks
- If no `git_url` on the project, prompts user to enter one
- Calls `POST /tasks/{id}/push`
- Shows success/error feedback

### Settings — GitHub Tab

- Single field: GitHub Personal Access Token
- Masked display when a value is stored
- Persisted via `PUT /settings` with key `github.token`
- Changes take effect on the next task execution (no service restart needed)

## Configuration

| Setting Key | Default | Description |
|-------------|---------|-------------|
| `github.token` | (empty) | GitHub Personal Access Token for clone/push |

## Cross-Context Dependencies

- **Task Lifecycle**: Push is triggered from the task detail page for completed tasks
- **Agent Execution**: Workers use git_utils for clone during task execution and push endpoint
- **Platform Infrastructure**: GitHub token stored in settings table; projects store git_url
