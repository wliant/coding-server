# Data Model: GitHub Token Integration (008)

## Changes to Existing Entities

### `jobs` table — add `branch` column

| Column   | Type         | Nullable | Default | Notes                                         |
|----------|--------------|----------|---------|-----------------------------------------------|
| `branch` | VARCHAR(255) | YES      | NULL    | Target branch for clone; NULL = default branch |

**Migration**: `api/alembic/versions/0008_add_branch_to_jobs.py`

```python
# upgrade
op.add_column("jobs", sa.Column("branch", sa.String(255), nullable=True))

# downgrade
op.drop_column("jobs", "branch")
```

**ORM (api)** — `api/src/api/models/job.py`:
```python
branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

**ORM (worker)** — `worker/src/worker/models.py` (mirror):
```python
branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

---

### `settings` table — add `github.token` key

No schema change required (existing key-value store). Changes to `api/src/api/services/setting_service.py`:

```python
ALLOWED_KEYS = {
    ...,
    "github.token",   # NEW
}

DEFAULTS = {
    ...,
    "github.token": "",   # NEW — empty string = not configured
}
```

No extra validation needed (any non-empty string is a valid token format).

---

## Schemas (Pydantic)

### `CreateTaskRequest` — add `branch`

File: `api/src/api/schemas/task.py`

```python
class CreateTaskRequest(BaseModel):
    ...
    branch: str | None = None   # NEW — target git branch; None = use default
```

### `TaskDetailResponse` — add `branch`

File: `api/src/api/schemas/task.py`

```python
class TaskDetailResponse(BaseModel):
    ...
    branch: str | None = None   # NEW — the branch associated with this task
```

---

## New Module: `worker/src/worker/git_utils.py`

```python
"""Git clone utilities for the worker."""

def inject_github_token(url: str, token: str) -> str:
    """
    Inject a GitHub token into an HTTPS URL.
    https://github.com/... → https://{token}@github.com/...
    No-op for SSH URLs or non-GitHub URLs.
    """

async def clone_repository(
    git_url: str,
    to_path: Path,
    branch: str | None = None,
    github_token: str = "",
) -> None:
    """
    Clone git_url into to_path.
    - If branch is set and exists on remote: clone and checkout that branch.
    - If branch is set but does not exist: clone default branch, create branch from HEAD.
    - If branch is None: clone default branch.
    - If github_token is set and URL is GitHub HTTPS: inject token into URL.
    - Raises CloneError (subclass of RuntimeError) on failure.
    """
```

---

## Helper: token injection for push

Location: `api/src/api/services/task_service.py` (private helper)

```python
def _inject_github_token(url: str, token: str) -> str:
    """Transform https://github.com/... → https://{token}@github.com/..."""
    if token and url.startswith("https://github.com"):
        return url.replace("https://", f"https://{token}@", 1)
    return url
```

Used inside `trigger_push()` — fetch `github.token` from settings then inject before calling `git_service.push_working_directory_to_remote()`.

---

## Worker dependency

Add to `worker/pyproject.toml`:

```toml
"gitpython>=3.1",
```

(GitPython is already used in the API; the worker needs it for cloning.)
