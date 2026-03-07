# Research: GitHub Token Integration (008)

## Decision 1: Token injection strategy for GitPython HTTPS auth

**Decision**: Embed the token directly in the HTTPS URL before passing to GitPython.

Transform `https://github.com/owner/repo.git` → `https://{token}@github.com/owner/repo.git`

**Rationale**: GitPython's `Repo.clone_from(url, path)` and remote push both consume a plain URL string. Embedding the token is the simplest approach — no credential-helper configuration, no environment variable injection, no subprocess wrapping. Consistent with how the existing `push_working_directory_to_remote()` function already accepts a `remote_url` string.

**Alternatives considered**:
- `GIT_ASKPASS` environment variable — more complex, subprocess-level, brittle in async contexts.
- System credential helper — requires host-level configuration; defeats the purpose of app-managed credentials.

---

## Decision 2: Clone function location

**Decision**: New module `worker/src/worker/git_utils.py` containing `clone_repository()`.

**Rationale**: The clone happens in the worker (before the agent runs), not in the API. The worker must not import from the API package. A dedicated `git_utils.py` in the worker keeps the concern isolated and testable independently from `agent_runner.py`. The API's `git_service.py` is unchanged — it already accepts a URL, so token injection in `task_service.py` before calling it is sufficient for push.

**Alternatives considered**:
- Shared library package — over-engineered for one function.
- Inline in `agent_runner.py` — harder to unit-test clone logic separately.

---

## Decision 3: Branch checkout strategy when branch doesn't exist remotely

**Decision**: Two-phase approach:
1. Try `Repo.clone_from(url, path, branch=branch_name)`.
2. On `git.GitCommandError` (branch not found on remote): clone without branch argument (gets default branch), then `repo.create_head(branch_name).checkout()`.

**Rationale**: GitPython raises `GitCommandError` when a specified branch doesn't exist on the remote. Catching this specific exception and falling back to default-branch-then-create is the minimal correct implementation. The result is a local branch named `branch_name` at the same commit as the default branch — ready for the agent to build on.

**Alternatives considered**:
- Pre-check branch existence via `ls-remote` — extra network round-trip, not needed.
- Always clone default, create branch — simpler code but loses the value of checking out an existing branch.

---

## Decision 4: Settings key and worker access

**Decision**: New setting key `github.token` (empty string default). Added to `ALLOWED_KEYS` and `DEFAULTS` in `api/src/api/services/setting_service.py`. No validation beyond type (string). Worker fetches all settings via `GET /settings` at agent start — `github.token` will be automatically included.

**Rationale**: Consistent with existing `openai_api_key` and `anthropic_api_key` keys. No extra infrastructure needed. Worker already calls `_fetch_agent_settings(api_url)` which returns the full settings dict.

**Alternatives considered**:
- Separate `/settings/github` endpoint — unnecessary indirection.
- Environment variable — requires container restart to change; not user-configurable at runtime.

---

## Decision 5: Push token injection location

**Decision**: In `task_service.trigger_push()`, call `await setting_service.get_settings(db)` to retrieve `github.token`. If set and URL is a GitHub HTTPS URL, inject token before calling `git_service.push_working_directory_to_remote()`. No changes to `git_service.py`.

**Rationale**: `task_service.py` already has the DB session and project data. Injecting at this layer keeps `git_service.py` token-agnostic (it just receives a URL). A helper `_inject_github_token(url, token)` function handles the URL transformation.

**Alternatives considered**:
- Modify `git_service.py` to accept an optional token — more interface churn, two callers to update.

---

## Decision 6: Latest Alembic migration

**Confirmed**: Latest migration is `0007`. New migration for `branch` column is `0008`.

---

## Decision 7: Worker gitpython dependency

**Confirmed**: Worker needs `gitpython` added to its dependencies if not already present (check `worker/pyproject.toml`). The API already uses it; the worker Dockerfile context is repo root.
