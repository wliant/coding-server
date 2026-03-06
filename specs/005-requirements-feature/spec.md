# Feature Specification: Automated Task Execution via Agent Worker

**Feature Branch**: `005-requirements-feature`
**Created**: 2026-03-06
**Status**: Draft
**Input**: User description: "implement the feature that will work on the requirements submitted"

## Clarifications

### Session 2026-03-06

- Q: Can users see only their own requirements, or is there a shared/global view? → A: Single-user application — no user concept, no authentication, no isolation needed.
- Q: What happens when the agent exceeds a processing time limit? → A: No timeout — tasks remain In Progress indefinitely until the agent produces a result or explicitly fails.
- Q: Can a submitted task be cancelled? → A: Cancellation (Abort) of a Pending task is already covered by spec 002-task-management-ui. Spec 005 must respect the Aborted status and not pick up Aborted tasks.
- Q: How is the generated code artifact delivered to the user? → A: No file download. A git remote URL is required. Once the agent completes its work, the working directory persists on disk and the user can trigger a push of the changes to the remote git repository from the UI.
- Q: Does the push go to the default branch or a new branch? → A: The worker creates a new branch named after the task and pushes that branch to the remote; the default branch of the repository MUST NOT be modified.

### Session 2026-03-06 (scope correction)

- Q: What is the actual scope of spec 005 relative to spec 002? → A: Spec 002 handles task submission, task listing, abort, edit, and settings UI. Spec 005 is the backend worker that picks up submitted tasks (status: Pending) from the system and executes them using the agents library in `./agents/`. "Requirement" in earlier drafts = "Task" in spec 002 terminology.
- Q: Where is the remote git URL stored — per-task, per-project, or in settings? → A: Per-task — a remote git URL field must be added to the task submission form in spec 002 so each task carries its own target repository URL.
- Q: How does the worker detect Pending tasks — polling or event-driven? → A: Polling on a fixed interval; the worker periodically queries the task store for Pending tasks.
- Q: Does the worker process tasks sequentially or concurrently? → A: Each worker instance processes exactly one task at a time. Multiple worker instances may run simultaneously; a lease pattern must be used to guarantee no two workers claim the same task.
- Q: What happens if a worker crashes while holding a lease? → A: Leases carry a TTL; the worker must renew the lease periodically while executing. If the lease expires without renewal, the task is automatically returned to Pending and becomes eligible for pickup by another worker.
- Q: Where does the Push action live in the UI? → A: A new task detail page is added (extending spec 002); the push action and execution output are shown there. The task list links to this detail page.

### Session 2026-03-06 (working directory & edge cases)

- Q: Is the working directory scoped per-project or per-task? → A: Per-task — the working directory is derived from `agent.work.path` + task ID/slug, fully isolating each task's output.
- Q: What happens if the push action is triggered more than once for the same task? → A: Re-triggering force-pushes the task branch, overwriting any existing remote branch of the same name.
- Q: What happens if the working directory cannot be created or accessed? → A: The worker marks the task as Failed with a descriptive error message; no retry is attempted.
- Q: What does the task detail page show while a task is In Progress? → A: Status and elapsed time only; no live agent logs. Full output appears once the task reaches Completed or Failed.
- Q: Where is LLM configuration sourced — environment variables, settings UI, or both? → A: Environment variables only. LLM provider, model, and API keys are never stored in the application database or exposed in the settings UI.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Worker Picks Up and Executes a Pending Task (Priority: P1)

When a task has been submitted (via spec 002) and is in Pending status, the worker automatically detects it, transitions it to In Progress, and invokes the appropriate coding agent from the agents library using the task's project name, requirements text, and configured working directory. Upon completion, the task is marked Completed or Failed.

**Why this priority**: This is the core value of spec 005 — without a worker executing tasks, submitted tasks never produce any output. All other stories depend on this running correctly.

**Independent Test**: Can be fully tested by creating a task with Pending status, starting the worker, and verifying the task transitions to In Progress then Completed (or Failed), with code changes written to the working directory.

**Acceptance Scenarios**:

1. **Given** a task is in Pending status, **When** the worker polls or is notified, **Then** the task transitions to In Progress before the agent begins executing.
2. **Given** a task is In Progress, **When** the coding agent completes successfully, **Then** the task transitions to Completed and code changes are present in the working directory.
3. **Given** a task is In Progress, **When** the coding agent encounters an error, **Then** the task transitions to Failed and the error details are stored against the task.
4. **Given** a task is in Aborted status, **When** the worker scans for work, **Then** the worker does NOT pick up or process that task.

---

### User Story 2 - Task Status Reflects Worker Progress (Priority: P2)

As the worker executes a task, the task's status transitions are immediately persisted so the existing task list UI (spec 002) reflects current progress without requiring manual intervention.

**Why this priority**: Status visibility is useless unless the worker keeps it accurate. The spec 002 UI already displays statuses — spec 005 must keep them correct.

**Independent Test**: Can be fully tested by watching the task list (spec 002 UI) refresh while the worker processes a task, observing Pending → In Progress → Completed/Failed transitions without any manual status change.

**Acceptance Scenarios**:

1. **Given** the worker picks up a task, **When** the task list is refreshed, **Then** the task shows In Progress status.
2. **Given** the agent completes, **When** the task list is refreshed, **Then** the task shows Completed or Failed status with any relevant error message.

---

### User Story 3 - Push Completed Task Changes to Remote Git (Priority: P3)

After the worker completes a task and code changes are present in the working directory, the user can trigger a push of those changes from the web interface. The worker creates a new branch named after the task and pushes it to the configured remote git URL; the repository's default branch is not modified.

**Why this priority**: Completing the loop from execution to delivery ensures the code changes reach their intended destination. Ranked P3 because it depends on P1 (agent producing output) and P2 (accurate status).

**Independent Test**: Can be tested by opening a completed task's detail page, triggering the push action, and verifying a new branch appears in the remote git repository.

**Acceptance Scenarios**:

1. **Given** a task is Completed, **When** the user opens the task detail page and triggers the push action, **Then** the worker creates a new branch named after the task and pushes it to the remote git URL stored on the task.
2. **Given** the push succeeds, **When** the detail page is refreshed, **Then** the UI confirms the branch name and remote URL where changes were pushed.
3. **Given** the push fails (e.g., remote unreachable, invalid credentials), **When** the push is attempted, **Then** a clear error message is shown on the detail page and the working directory changes remain intact.
4. **Given** a task is Failed, **When** the task detail page is viewed, **Then** the push action is not available.

---

### Edge Cases

- If the working directory cannot be created or accessed, the worker marks the task as Failed immediately with a descriptive error message; no retry is attempted (consistent with FR-004/FR-005).
- Multiple worker instances may be active simultaneously; the lease pattern ensures each task is claimed by exactly one worker. If two workers attempt to claim the same task concurrently, only one succeeds and the other moves on.
- There is no processing timeout — a task remains In Progress until the agent explicitly concludes; the system must accurately reflect this state.
- What happens if the git remote URL is invalid or unreachable at push time? (Error shown; working directory preserved.)
- If a worker crashes mid-execution, its lease expires and the task automatically returns to Pending for pickup by another worker; the previously written working directory contents may be partially complete.

## Requirements *(mandatory)*

### Functional Requirements

**Task Execution**

- **FR-001**: The worker MUST poll the task store on a fixed interval to detect Pending tasks.
- **FR-001a**: Before processing a task, the worker MUST acquire an exclusive lease on that task using a lease pattern (atomic compare-and-set or equivalent), ensuring no two worker instances can claim the same task simultaneously.
- **FR-001b**: Only after successfully acquiring the lease MUST the worker transition the task to In Progress and begin execution. If lease acquisition fails, the worker skips that task and continues polling.
- **FR-001c**: Each lease MUST carry a TTL. The worker MUST renew the lease at regular intervals while executing. If a lease expires without renewal (e.g., worker crash), the system MUST automatically return the task to Pending so another worker can claim it.
- **FR-002**: The worker MUST NOT process tasks in Aborted, In Progress, Completed, or Failed status.
- **FR-003**: The worker MUST invoke the coding agent (`simple_crewai_pair_agent.CodingAgent`) with the task's `project_name`, `requirement` text, and a `working_directory` derived from `agent.work.path` + task ID or slug — one isolated directory per task, regardless of project.
- **FR-004**: The worker MUST transition the task to Completed when the agent returns a successful result, and to Failed when the agent raises an exception or returns an error result.
- **FR-005**: The worker MUST persist error details (message or stack trace summary) against a Failed task so they are retrievable via the task detail view.
- **FR-006**: The working directory used for a task MUST persist after agent completion and MUST NOT be automatically cleaned up.

**Task Detail Page**

- **FR-007**: The system MUST provide a task detail page (extending spec 002) accessible by clicking a task from the task list. The detail page MUST display:
  - All statuses: task title, requirements text, remote git URL, current status, working directory path
  - In Progress only: elapsed time since the task started; no live agent logs
  - Completed only: Push to Remote action
  - Failed only: human-readable error message; no Push to Remote action

**Git Push**

- **FR-008**: On a Completed task, the detail page MUST expose a "Push to Remote" action.
- **FR-009**: When triggered, the push action MUST create or update a git branch in the working directory named after the task (using the task's unique identifier or title slug) and force-push that branch to the remote git URL stored on the task. Re-triggering the push overwrites any existing remote branch of the same name.
- **FR-010**: The push action MUST NOT commit to or modify the default branch of the remote repository.
- **FR-011**: If the push fails, the system MUST display a clear, actionable error message on the detail page and leave the working directory unchanged.
- **FR-012**: The push action MUST NOT be available for tasks in Failed, In Progress, Pending, or Aborted status.

**Agent Configuration**

- **FR-013**: The worker MUST read the agent working directory base path from the system settings (`agent.work.path`) as configured via spec 002.
- **FR-014**: The worker MUST read LLM provider, model name, and API keys exclusively from environment variables. These values MUST NOT be hardcoded, stored in the application database, or exposed in the settings UI.

### Key Entities

- **Task**: Defined by spec 002. Relevant attributes for spec 005: unique ID, project name, requirements text, remote git URL (new field, collected at submission via spec 002 update), status (Pending / In Progress / Completed / Failed / Aborted), error details, lease holder (worker identity), lease expiry timestamp — both set atomically during lease acquisition and renewed periodically.
- **Working Directory**: The on-disk path where the agent writes code changes for a given task. Derived from `agent.work.path` + task ID or slug — one directory per task, fully isolated. Persists after completion.
- **Agent Execution**: The invocation of `CodingAgent` for a task. Inputs: `working_directory`, `project_name`, `requirement`. Output: `CodingAgentResult` (success or error).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Pending task transitions to In Progress within one polling interval of becoming Pending (target: within 10 seconds).
- **SC-002**: 90% of clearly stated tasks result in code changes written to the working directory and a Completed status.
- **SC-003**: Task status transitions (In Progress, Completed, Failed) are persisted and visible via task list refresh within 10 seconds of the agent state change.
- **SC-004**: A push triggered from a Completed task results in a new branch appearing in the remote git repository within 30 seconds under normal network conditions.
- **SC-005**: 100% of Failed tasks have a non-generic, human-readable error message stored and visible in the task detail view.

## Assumptions

- This is a single-user application with no authentication or per-user data isolation.
- Task submission, task listing, abort, edit, and settings UI are all handled by spec 002. Spec 005 adds one new UI page: a task detail page accessible from the task list, which shows execution output and the push action.
- The only fully implemented agent is `simple_crewai_pair_agent` (`CodingAgent`); the worker uses this agent for all task types in this iteration.
- The agent working directory base path (`agent.work.path`) is already stored in system settings as defined by spec 002 (FR-003 of that spec).
- Real-time status push (e.g., WebSocket) is out of scope; polling on a manual refresh is acceptable for this version.
- Git credentials (SSH keys or token) are pre-configured in the server environment; the user does not supply git credentials through the UI.
- The `CodingAgentResult` from `simple_crewai_pair_agent` is sufficient to determine success or failure; no additional post-processing of the output is required.
- The remote git URL is stored per-task; spec 002's task submission form must be updated to include a mandatory remote git URL field. This is a cross-spec dependency: spec 005 cannot push changes without the URL being present on the task record.
