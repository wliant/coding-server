# Feature Specification: Agent Controller / Worker Redesign

**Feature Branch**: `009-agent-controller-worker`
**Created**: 2026-03-08
**Status**: Draft

## Overview

Replace the current timer-based, lease-claiming worker with a dedicated **Controller** service and one or more **Worker** services. The Controller is the central coordinator: it polls for pending tasks, matches them to available workers by agent type, delegates work, monitors worker health, and renews task claims while work is in progress. Workers are independent services that register with the Controller, receive and execute tasks, report status, and expose APIs for push operations and post-task cleanup.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Worker Registers and Receives Tasks (Priority: P1)

A system operator starts one or more worker services. Each worker automatically registers with the Controller on startup, receives a unique worker ID, and becomes eligible to receive tasks that match its configured agent type. The Controller identifies pending tasks and delegates them to free workers.

**Why this priority**: This is the foundational flow. Without registration and delegation, no work can happen. Everything else builds on this.

**Independent Test**: Start one controller and one worker. Submit a task for the matching agent type. Confirm the task is delegated to the worker and transitions to in-progress.

**Acceptance Scenarios**:

1. **Given** a worker starts with a valid Controller URL and agent type configured, **When** the worker calls the registration endpoint, **Then** the Controller responds with a unique worker ID and the worker appears in the worker list with status "free".
2. **Given** a registered worker with status "free" and a pending task matching its agent type, **When** the Controller's polling cycle runs, **Then** the task is delegated to that worker, the task status changes to "in_progress", and the worker status changes to "in_progress".
3. **Given** no registered free workers match the pending task's agent type, **When** the Controller's polling cycle runs, **Then** the task remains in "pending" state and no delegation occurs.

---

### User Story 2 — Task Execution and Completion Reporting (Priority: P1)

After the Controller delegates a task, the worker executes it (cloning the repository if applicable, running the agent) and reports the outcome back to the Controller. The task transitions to "completed" or "failed", and the worker transitions to "completed" or "failed" state — not yet free, awaiting user-initiated cleanup.

**Why this priority**: Task execution and outcome reporting are the core value of the system.

**Independent Test**: With a registered free worker, delegate a task. Observe the worker execute it and report completion. Verify task status and worker status both reflect the outcome.

**Acceptance Scenarios**:

1. **Given** a worker receives a task for an existing project with a git URL and branch, **When** the worker begins execution, **Then** the worker clones the repository and checks out the specified branch (or creates it from the default branch if it doesn't exist remotely) before running the agent.
2. **Given** a worker completes execution successfully, **When** it reports the result to the Controller, **Then** the task status transitions to "completed" and the worker status transitions to "completed".
3. **Given** a worker encounters an error during execution, **When** it reports the failure, **Then** the task status transitions to "failed" and the worker status transitions to "failed".
4. **Given** a task transitions to "completed" or "failed", **When** a user views the task list, **Then** the user sees a "Clean Up" button alongside the task.

---

### User Story 3 — Worker Health Monitoring and Lease Renewal (Priority: P2)

Workers periodically send heartbeats to the Controller to signal they are still alive. The Controller refreshes the task's lease while the worker is healthy. If a worker stops sending heartbeats (crash or hang), the Controller marks it as unreachable and releases the lease so another worker can pick up the task.

**Why this priority**: Without health monitoring, stuck or crashed workers silently block tasks indefinitely.

**Independent Test**: Start a worker, assign it a task, then simulate a crash (stop heartbeats). Verify the Controller detects the dead worker and the task becomes reclaimable after the timeout.

**Acceptance Scenarios**:

1. **Given** a worker is executing a task and sending regular heartbeats, **When** the Controller's lease renewal cycle runs, **Then** the task's lease is refreshed and the task does not become reclaimable.
2. **Given** a worker stops sending heartbeats, **When** the heartbeat timeout period elapses, **Then** the Controller marks the worker as unreachable and releases the task lease so it can be delegated to another free matching worker.
3. **Given** registered workers, **When** a user queries the Controller's worker list endpoint, **Then** each worker's last heartbeat timestamp is included in the response.

---

### User Story 4 — Post-Task Cleanup (Priority: P2)

After a task reaches "completed" or "failed", the worker holds its working directory and is not free to accept new tasks. A user explicitly initiates cleanup, which causes the Controller to instruct the worker to delete its working directory and free itself. The task transitions to "cleaned" and the worker returns to "free" status.

**Why this priority**: Without cleanup, workers become permanently occupied after their first task.

**Independent Test**: Complete a task. Click "Clean Up" in the UI. Verify the working directory is deleted, the task moves to "cleaned", and the worker accepts a new task.

**Acceptance Scenarios**:

1. **Given** a task in "completed" or "failed" state, **When** a user clicks "Clean Up", **Then** the task transitions to "cleaning_up" and the Controller calls the worker's free endpoint.
2. **Given** the worker receives a free request while in "completed" or "failed" state, **When** it successfully deletes its working directory, **Then** the task transitions to "cleaned" and the worker status returns to "free".
3. **Given** the worker fails to delete the working directory, **When** it reports the failure, **Then** the task remains in "cleaning_up" state and an error is visible to the user.

---

### User Story 5 — Worker Status Visibility in the UI (Priority: P3)

System operators can view the current status of all registered workers — their assigned agent type, current task (if any), status, and last heartbeat time — via a dedicated Workers page (`/workers`) accessible from the main navigation.

**Why this priority**: Operational visibility aids troubleshooting but is not blocking for core execution.

**Independent Test**: Register two workers. Navigate to the workers view. Confirm both appear with correct status, agent type, and heartbeat information.

**Acceptance Scenarios**:

1. **Given** multiple workers are registered, **When** a user navigates to the `/workers` page, **Then** each worker is shown with its ID, agent type, status, current task ID (if any), and last heartbeat timestamp.
2. **Given** a worker transitions from "free" to "in_progress", **When** the user refreshes the workers list, **Then** the updated status and associated task are reflected.

---

### User Story 6 — Git Push via Worker (Priority: P3)

After a task completes, a user can push the agent's output to the remote git repository through the worker. The push uses any configured GitHub token for authentication.

**Why this priority**: Push is a follow-on action after task completion; core execution is higher priority.

**Independent Test**: Complete a task for an existing project. Trigger the push action. Verify the working directory contents are pushed to the remote.

**Acceptance Scenarios**:

1. **Given** a completed task for a project with a git URL, **When** a user initiates a push, **Then** the worker pushes the working directory contents to the remote and reports success.
2. **Given** a push is initiated without a configured git URL, **Then** the system returns an error indicating no remote is configured.

---

### Edge Cases

- What happens when the Controller restarts while workers are mid-task? The worker registry is in-memory and is lost on Controller restart. Workers MUST automatically retry registration with the Controller on startup and periodically until successful. Leases for in-progress tasks will expire after the heartbeat timeout and the tasks will revert to "pending" for re-delegation once workers re-register.
- What happens when a worker restarts mid-task? Its heartbeat stops; after timeout the lease is released and the task can be reassigned.
- What happens when the working directory does not exist when cleanup is requested? The worker treats it as already cleaned and reports success.
- What happens when a task's agent type has no registered free workers? The task remains pending until a matching worker becomes available.
- What happens when a worker is "in_progress" and the Controller tries to assign another task? The Controller must not assign a second task to an occupied worker.
- What happens if the Controller cannot reach the worker's work endpoint during delegation? The Controller must release the task claim and leave the task in "pending" state for retry.

---

## Requirements *(mandatory)*

### Functional Requirements

**Controller Service**

- **FR-001**: The Controller MUST expose an endpoint for workers to register, accepting the worker's agent type and a self-reported URL, and returning a unique worker ID.
- **FR-002**: The Controller MUST expose an endpoint for workers to send heartbeats, updating the worker's last-seen timestamp.
- **FR-003**: The Controller MUST expose a liveness endpoint that external clients can use to verify the Controller is operational.
- **FR-004**: The Controller MUST expose an endpoint listing all registered workers with their IDs, agent types, statuses, current task IDs, and last heartbeat timestamps.
- **FR-005**: The Controller MUST periodically poll the main application database directly (using its own DB connection) for pending tasks and match each task to a free registered worker of the correct agent type.
- **FR-006**: When delegating a task, the Controller MUST atomically claim the task for the selected worker ID before calling the worker's work endpoint, preventing double-delegation.
- **FR-007**: The Controller MUST periodically refresh the lease of any claimed task while the assigned worker is sending heartbeats within the configured timeout.
- **FR-008**: When a worker's heartbeat has not been received within the configured timeout, the Controller MUST mark the worker as unreachable and release the task lease.
- **FR-009**: When a task transitions to "cleaning_up", the Controller MUST call the worker's free endpoint to initiate working directory deletion.

**Worker Service**

- **FR-010**: Each worker MUST have a configured working directory path where it stores files for the current task.
- **FR-011**: Each worker MUST have a configured agent type that determines which kinds of tasks it can execute.
- **FR-012**: Each worker MUST have a configured Controller URL and MUST register with the Controller on startup, with automatic retry until registration succeeds (to handle Controller restarts or delayed startup).
- **FR-013**: Each worker MUST periodically send heartbeats to the Controller while running.
- **FR-014**: The worker MUST expose an endpoint for the Controller to issue work (deliver a task to execute).
- **FR-015**: The worker MUST expose an endpoint returning its current status: free, in_progress, completed, or failed.
- **FR-016**: When a task involves an existing project with a git URL, the worker MUST clone the repository into its working directory and check out the specified branch before running the agent. If the branch does not exist remotely, the worker MUST create it from the default branch.
- **FR-017**: The worker MUST expose an endpoint for initiating a git push of the working directory contents to the remote repository.
- **FR-018**: The worker MUST expose a free endpoint for the Controller to request cleanup; on success the worker MUST delete its working directory and return its status to "free".
- **FR-019**: Each worker MUST maintain its own persistent state (current task ID, execution status, execution logs) in a dedicated database schema separate from the main application database.
- **FR-020**: After completing or failing a task, the worker MUST NOT accept new tasks until cleanup is performed and its status returns to "free".

**Task Lifecycle**

- **FR-021**: The task status model MUST be extended with two additional statuses: "cleaning_up" (cleanup initiated, in progress) and "cleaned" (cleanup complete, terminal state).
- **FR-022**: The "Clean Up" action MUST be available to users on tasks in "completed" or "failed" state.
- **FR-023**: The `agent.work.path` general setting MUST be removed from the Settings UI and no longer used, as each worker self-configures its working directory.
- **FR-024**: The existing timer-based worker service MUST be fully decommissioned and removed from the deployment as part of this feature. No coexistence with the old worker is required.

### Key Entities

- **Controller**: Central coordination service. Maintains the worker registry, polls for pending tasks, delegates work, monitors heartbeats, renews leases, and orchestrates cleanup.
- **Worker**: Independent execution service. Configured with an agent type, working directory path, and Controller URL. Executes one task at a time. Maintains its own state database. Statuses: free, in_progress, completed, failed.
- **WorkerRegistration**: Record kept by the Controller for each registered worker. Fields: worker ID (assigned by Controller), agent type, worker URL, status, last heartbeat timestamp, current task ID (nullable), registered-at timestamp.
- **Task** (extended): Gains two new terminal-side statuses — "cleaning_up" and "cleaned" — and a new field tracking the assigned worker ID.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A newly started worker registers with the Controller and appears in the worker list within 5 seconds of startup.
- **SC-002**: A pending task is delegated to a matching free worker within two Controller polling intervals of the worker becoming available.
- **SC-003**: A worker that stops sending heartbeats is detected as unreachable and its task lease is released within the configured heartbeat timeout (default: 60 seconds).
- **SC-004**: The full cleanup flow (user initiates → working directory deleted → worker status "free") completes within 30 seconds under normal conditions.
- **SC-005**: Multiple workers of the same agent type can run concurrently without any task being double-delegated.
- **SC-006**: After a Controller restart, in-progress tasks whose leases expire are automatically returned to "pending" and re-delegated to available workers.
- **SC-007**: The `/workers` page displays accurate status for all registered workers, with information no more than one polling interval stale, and is accessible from the main navigation.

---

## Assumptions

- A single Controller instance per deployment is sufficient; multi-controller high-availability is out of scope.
- The Controller's worker registry is held in-memory only and is not persisted to any database. A Controller restart clears all registrations; workers are responsible for re-registering automatically.
- Each worker executes exactly one agent type; a worker serving multiple agent types is out of scope.
- The Controller and workers communicate over HTTP within the same internal network with no inter-service authentication. Network isolation is the sole protection for worker API endpoints.
- Worker working directories are local to the worker container or host; no shared filesystem between workers is assumed.
- The worker's own database schema resides on the same database server as the main application but uses a distinct schema or table prefix to avoid conflicts.
- Heartbeat timeout and polling interval are configurable via environment variables with sensible defaults (e.g., 60-second heartbeat timeout, 10-second polling interval).
- The Controller is the sole entity responsible for lease management on the main jobs table; workers do not directly update lease fields. The Controller has its own direct database connection to the same database as the main API.
- The existing `agent.work.path` setting value in any deployed instance can be ignored; no data migration is needed.
- The existing timer-based worker service is fully replaced by the new Controller + Worker services. The old worker is removed from the deployment; no coexistence period is required.

---

## Clarifications

### Session 2026-03-08

- Q: Where does the Controller persist its worker registry (in-memory vs database)? → A: In-memory only — registry lost on Controller restart; workers must re-register automatically.
- Q: Does the Controller access the jobs/tasks database directly or via the main API's HTTP endpoints? → A: Direct DB access — Controller connects to the same database as the main API and reads/writes the jobs table directly.
- Q: What authentication protects the worker's APIs (receive work, push, free)? → A: No authentication — worker APIs are open; network isolation is the only protection.
- Q: Is the existing worker service replaced or kept alongside the new services? → A: Full replacement — existing worker service is removed; Controller + new worker services replace it entirely.
- Q: Where is the workers status view located in the UI navigation? → A: Dedicated page — a new `/workers` route with its own navigation link.
