# Quickstart: GitHub Token Integration (008)

## Prerequisites

- Docker + `task` (Taskfile) installed
- A GitHub account with a Personal Access Token (classic or fine-grained with `repo` scope)

## End-to-End Verification

### 1. Start the dev environment

```bash
task dev
```

### 2. Configure the GitHub token

1. Open `http://localhost:3000/settings`
2. Click the **GitHub** tab
3. Enter your token in the **GitHub Token** field
4. Click **Save** — you should see "Settings saved successfully"
5. Refresh the page — the token field should show a masked value (e.g., `••••••••`)

### 3. Create a project with a GitHub repository URL

When submitting a new task, select **Existing project** and enter a GitHub HTTPS URL:
```
https://github.com/your-org/your-repo.git
```
Optionally specify a branch name (e.g., `feature/my-work`).

### 4. Submit the task and verify clone

1. Submit the task
2. Watch the task status transition to `in_progress`
3. The worker log should show `clone_started` and `clone_succeeded` events
4. The task detail page's work directory should contain the cloned repository files

### 5. Verify push uses the token

1. Once the task completes, click **Push to Remote**
2. The push should succeed for private repositories without any system-level git configuration
3. Check GitHub — the branch `task/{first-8-chars-of-task-id}` should appear in the repository

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Task fails with "clone failed: authentication" | Token missing or expired | Refresh token in Settings → GitHub tab |
| Task fails with "clone failed: repository not found" | Wrong git_url | Check the URL on GitHub |
| Task fails with "clone failed: branch X not found... created from default" | Branch was auto-created | This is expected behavior — the branch is created locally, not pushed until task completes |
| Push fails with 401/403 | Token lacks `repo` write scope | Re-generate token with `repo` scope |
| Worker log shows `gitpython not installed` | Worker image not rebuilt | `docker compose build worker` |

## Running Tests

```bash
# API tests (includes migration + task schema tests)
docker compose -f compose.yaml -f compose.dev.yaml exec api pytest tests/

# Worker tests (includes git_utils tests)
docker compose -f compose.yaml -f compose.dev.yaml exec worker pytest tests/

# Frontend type check
cd web && npx tsc --noEmit
```
