# Research: Automated Task Execution via Agent Worker

**Feature**: 005-requirements-feature | **Date**: 2026-03-06

## 1. DB-Based Lease / Optimistic Locking for Worker Claim

**Decision**: Use a conditional `UPDATE` with `WHERE status = 'pending'` on the `jobs` table to atomically claim a job, setting `status = 'in_progress'`, `lease_holder = <worker_uuid>`, and `lease_expires_at = now() + TTL`. PostgreSQL's MVCC guarantees only one writer wins a concurrent UPDATE on the same row.

**Rationale**: The existing stack already uses SQLAlchemy async + asyncpg. A single atomic UPDATE is the simplest correct solution — no Redis locks, no `SELECT FOR UPDATE SKIP LOCKED` complexity, no distributed coordination service. SQLAlchemy's `update().where().returning()` pattern expresses this cleanly.

**Lease reaper**: The worker polling loop also queries for jobs with `status = 'in_progress' AND lease_expires_at < now()` and resets them to `status = 'pending', lease_holder = NULL, lease_expires_at = NULL`. This runs in the same poll cycle.

**Lease renewal**: A background `asyncio.Task` renews `lease_expires_at = now() + TTL` for the currently active job every `LEASE_TTL / 2` seconds while the agent is running.

**Alternatives considered**:
- `SELECT FOR UPDATE SKIP LOCKED`: More complex, requires explicit transaction management; the atomic UPDATE approach is equivalent and simpler.
- Redis-based distributed lock (`SET NX PX`): Adds a Redis dependency for leasing when the DB is already present; rejected per Simplicity-First.
- Advisory locks (`pg_try_advisory_xact_lock`): PostgreSQL-specific, harder to reason about in async context; rejected.

---

## 2. Working Directory Isolation Per Task

**Decision**: Working directory path = `{AGENT_WORK_PARENT}/{job_id}`. Uses the existing `WorkDirectory` model to record the path. The `WorkDirectory` record is created by the worker before invoking the agent.

**Rationale**: Using `job_id` (UUID) as the directory name guarantees uniqueness across all tasks and projects. The `WorkDirectory` table already enforces `UNIQUE(job_id)` and `UNIQUE(path)`. The API's git push service reads `WorkDirectory.path` via the `job_id`.

**Alternatives considered**:
- `{AGENT_WORK_PARENT}/{project_name}/{job_id}`: Adds project-name path segment for human readability, but creates directory collision risk if project name changes; rejected.
- `{AGENT_WORK_PARENT}/{project_name}` (per-project): Multiple tasks on the same project share a directory; rejected per spec clarification (per-task isolation required).

---

## 3. Git Push Implementation

**Decision**: Use `gitpython` (`git` Python library) via the API's `git_service.py`. The API container mounts the same `agent_work` volume as the worker. On `POST /tasks/{id}/push`, the service:
1. Reads `WorkDirectory.path` for the job.
2. Opens the git repo at that path (`git.Repo(path)`).
3. Creates or resets a branch named `task/{job_id_short}` (first 8 chars of UUID).
4. Force-pushes the branch to `Project.git_url`.

**Rationale**: `gitpython` is a well-maintained Python library that wraps `git` CLI operations, avoiding subprocess shell injection risks. The API already has DB access to retrieve `WorkDirectory.path` and `Project.git_url`. Force-push is correct for idempotent re-push (per spec clarification).

**Branch naming**: `task/{job_id_short}` — short, collision-resistant, human-readable in the remote.

**Alternatives considered**:
- `subprocess.run(['git', ...])`: Works but requires shell escaping and manual error parsing; `gitpython` is safer.
- Worker handles git push directly: Would require the worker to expose an internal endpoint or message queue; rejected for added complexity — the API can access the shared volume.
- Full `job_id` as branch name: Too long for git branch names in some UIs; short form (8 chars) is sufficient for uniqueness at this scale.

---

## 4. `simple_crewai_pair_agent` Interface

**Decision**: Invoke via:
```python
from simple_crewai_pair_agent import CodingAgent, CodingAgentConfig, CodingAgentResult

config = CodingAgentConfig(
    working_directory=Path(work_dir_path),
    project_name=job.project_name,       # from Project.name or job UUID if name is None
    requirement=job.requirement,
    llm_provider=settings.LLM_PROVIDER,  # from env var
    llm_model=settings.LLM_MODEL,        # from env var
    ollama_base_url=settings.OLLAMA_BASE_URL,
    openai_api_key=settings.OPENAI_API_KEY,
    anthropic_api_key=settings.ANTHROPIC_API_KEY,
)
result: CodingAgentResult = CodingAgent(config).run()
```

**Result handling**: `CodingAgent.run()` returns a `CodingAgentResult`. On exception, catch `Exception` and treat as failure. Inspect `CodingAgentResult` for success/error signal (to be confirmed during implementation against actual `result.py`).

**Project name fallback**: If `Project.name` is `None` (new project without a name), use `str(job.id)[:8]` as the project name passed to the agent.

**Alternatives considered**:
- Passing `project_id` as project_name: Not human-readable in agent context; full name or short UUID is better.

---

## 5. LLM Configuration via Environment Variables

**Decision**: Extend `worker/src/worker/config.py` (`Settings` class) with:
- `LLM_PROVIDER: str = "ollama"`
- `LLM_MODEL: str = "qwen2.5-coder:7b"`
- `LLM_TEMPERATURE: float = 0.2`
- `OLLAMA_BASE_URL: str = "http://localhost:11434"`
- `OPENAI_API_KEY: str = "NA"`
- `ANTHROPIC_API_KEY: str = ""`

These are read-only at worker startup; changing them requires a worker restart. Not stored in DB or settings UI (per spec clarification).

**Rationale**: Mirrors `CodingAgentConfig` defaults. Pydantic `BaseSettings` reads from environment variables and `.env` file, consistent with existing config pattern.

---

## 6. Polling Interval and Lease TTL

**Decision**:
- `POLL_INTERVAL_SECONDS = 5` — poll every 5 seconds (well within 10 s SC-001 target)
- `LEASE_TTL_SECONDS = 300` — 5-minute lease (long-running agents may take minutes)
- `LEASE_RENEWAL_INTERVAL_SECONDS = 120` — renew every 2 minutes (< TTL/2)

**Rationale**: 5-second polling gives responsive pickup without hammering the DB. 5-minute TTL gives agents ample time before lease expiry risk; renewal at 2 minutes provides a 3-minute safety buffer for a stuck renewal. These are env-var configurable for easy tuning.
