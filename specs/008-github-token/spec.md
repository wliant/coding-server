# Feature Specification: GitHub Token Integration

**Feature Branch**: `008-github-token`
**Created**: 2026-03-07
**Status**: Draft
**Input**: User description: "Github integration feature — add a settings for github token. When cloning a repository to work on, use this token. When pushing a repository, also use this token."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure GitHub Token in Settings (Priority: P1)

A user navigates to the Settings page, opens the dedicated **GitHub** section, and enters their GitHub Personal Access Token. Once saved, the token is persisted and used for all subsequent GitHub operations (clone and push). The user can update or clear the token at any time.

**Why this priority**: All other GitHub-related functionality depends on the token being stored. This is the foundation for the feature.

**Independent Test**: Can be fully tested by opening Settings, entering a token, saving, refreshing the page, and confirming the token value is retained — before any clone or push operation is performed.

**Acceptance Scenarios**:

1. **Given** no GitHub token is configured, **When** the user opens the GitHub section of Settings, **Then** the GitHub Token field is empty and a placeholder prompt is shown.
2. **Given** the user enters a token and clicks Save, **When** the save succeeds, **Then** a success confirmation is shown and the token is persisted.
3. **Given** a token is saved, **When** the user returns to Settings, **Then** the token field is pre-populated with a masked display of the saved token (e.g., shown as `•••••••` or last 4 characters visible).
4. **Given** a token is saved, **When** the user clears the field and saves, **Then** the token is removed and future operations proceed without authentication.

---

### User Story 2 - Clone Repository Before Agent Starts (Priority: P2)

When a task is submitted for a project that has a Git URL configured, the user optionally specifies a branch name on the task. The worker clones the repository and checks out that branch before the coding agent begins work. If the specified branch does not exist on the remote, it is created from the default branch. If no branch is specified, the default branch is used. If a GitHub token is configured, it is used to authenticate the clone operation.

**Why this priority**: This enables agents to start from existing project code rather than an empty directory, which is essential for most real-world coding tasks.

**Independent Test**: Can be fully tested by creating a project with a GitHub URL, submitting a task with a branch name, and verifying the working directory contains the repository contents on the correct branch when the agent starts — observable via task logs or the work directory.

**Acceptance Scenarios**:

1. **Given** a project with a GitHub URL and a configured token, **When** a task starts, **Then** the working directory is populated with the cloned repository before the agent runs.
2. **Given** a task with a branch name that exists on the remote, **When** the task starts, **Then** the working directory is on that branch.
3. **Given** a task with a branch name that does not exist on the remote, **When** the task starts, **Then** the system clones the default branch and creates the specified branch from it; the working directory is on the new branch.
4. **Given** a task with no branch name specified, **When** the task starts, **Then** the default branch is cloned and checked out.
5. **Given** a project with a GitHub URL but no token configured, **When** a task starts, **Then** the system attempts to clone without authentication (succeeds for public repos, fails gracefully for private repos).
6. **Given** a project with no Git URL, **When** a task starts, **Then** the working directory starts empty (current behavior unchanged).
7. **Given** a project with a GitHub URL and a valid token, **When** the clone fails (e.g., repo not found, invalid token), **Then** the task transitions to `failed` with a clear error message explaining the clone failure.
8. **Given** a project with a GitHub URL and an invalid token, **When** a task starts, **Then** the task fails immediately with an authentication error rather than starting the agent.

---

### User Story 3 - Push Work to GitHub Using Token (Priority: P3)

When a user triggers "Push to Remote" on a completed task, the system uses the configured GitHub token to authenticate the push operation — without relying on system-level SSH keys or credential helpers.

**Why this priority**: Completes the full round-trip GitHub workflow. Depends on the token setting (P1) being available. Less critical than cloning because push is a manual action.

**Independent Test**: Can be fully tested by completing a task with a GitHub-hosted project and clicking "Push to Remote", then verifying the branch appears on GitHub.

**Acceptance Scenarios**:

1. **Given** a completed task, a configured GitHub token, and a project with a GitHub URL, **When** the user clicks "Push to Remote", **Then** the push succeeds using the token for authentication.
2. **Given** a completed task with no GitHub token configured, **When** the user clicks "Push to Remote", **Then** the push is attempted without token-based auth (same behavior as today — succeeds if system credentials are available).
3. **Given** a completed task with an invalid or expired token, **When** the user clicks "Push to Remote", **Then** the operation fails with a clear error message indicating an authentication problem.

---

### Edge Cases

- What happens when the GitHub token has insufficient permissions (e.g., read-only token used for push)? → The operation fails with a clear permission error, not a generic failure.
- What happens if the configured token is valid but the repository URL does not belong to GitHub? → Token-based auth is applied only for GitHub URLs; other hosts are unaffected.
- What if the token is changed between when a task starts cloning and when the push happens? → Each operation reads the current token at the time it runs; there is no caching per-task.
- What happens if the clone takes a very long time (large repository)? → The task remains `in_progress` during cloning; a timeout or size limit is not enforced by this feature.
- What happens if a branch name is specified but the clone itself fails (e.g., repo not found)? → The task fails with a clone error; branch creation is never attempted.
- What if a task has no branch specified and the project has no Git URL? → Working directory starts empty, identical to today's behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to save a GitHub Personal Access Token via a dedicated **GitHub** section in the Settings page (separate from General and Agent settings sections).
- **FR-002**: The stored token MUST be masked in the UI (not displayed in plain text after saving).
- **FR-003**: Users MUST be able to update or clear the token at any time via Settings.
- **FR-004**: When a task is started for a project with a Git URL, the system MUST clone the repository into the task's working directory before the agent begins.
- **FR-004a**: A task submission MUST accept an optional `branch` field specifying which branch to check out after cloning.
- **FR-004b**: If the specified branch exists on the remote, the system MUST check it out; if it does not exist, the system MUST create it from the remote default branch.
- **FR-004c**: If no branch is specified on the task, the default branch of the repository MUST be used.
- **FR-005**: When cloning, the system MUST use the configured GitHub token for authentication if one is set and the URL is a GitHub URL.
- **FR-006**: When a clone fails, the task MUST transition to `failed` status with a descriptive error message; the agent MUST NOT run on a failed clone.
- **FR-007**: When pushing a completed task's work to a remote GitHub repository, the system MUST use the configured GitHub token for authentication if one is set.
- **FR-008**: If no GitHub token is configured, clone and push operations MUST proceed without token-based authentication (preserving current behavior for unauthenticated/SSH scenarios).
- **FR-009**: The token MUST be stored using the existing settings key-value store, consistent with how other credentials (e.g., OpenAI API key) are handled today.

### Key Entities

- **GitHub Token Setting**: A stored credential (key: `github.token`) in the global settings store. Single value, shared across all projects and tasks. Treated as a secret; masked in all UI displays.
- **Project**: Already has a `git_url` field (nullable). This feature adds meaning: when populated with a GitHub URL, it drives both clone (on task start) and push (on push action).
- **Task**: Gains an optional `branch` field (nullable string). When set, directs which branch the worker checks out after cloning; if the branch doesn't exist remotely, it is created from the default branch.
- **Task Work Directory**: The directory where agent work happens. This feature adds a pre-agent step: the work directory is populated by cloning before the agent starts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can enter, save, and retrieve a GitHub token from the Settings page in under 30 seconds.
- **SC-002**: 100% of tasks for projects with a configured GitHub URL start with the repository already cloned into the working directory (no manual setup required).
- **SC-003**: Push to Remote succeeds for private GitHub repositories when a valid token with write access is configured, with no additional system configuration needed.
- **SC-004**: Clone failures produce a human-readable error visible on the task detail page within 10 seconds of failure.
- **SC-005**: Removing the GitHub token from Settings immediately affects the next operation; no stale credentials are used.

## Assumptions

- The GitHub token is a single global credential shared across all projects. Per-project tokens are out of scope.
- Token masking in the UI uses a standard password-style display; the raw token value is never shown after initial save.
- "GitHub URL" means any URL matching `github.com` — token auth is applied only to these URLs, not arbitrary git hosts.
- Cloning is triggered automatically by the worker when the project has a `git_url`; no per-task opt-in is needed.
- The GitHub token is stored using the same settings infrastructure as existing API keys (`ALLOWED_KEYS` allowlist, key-value DB table).
- If the git URL is an SSH URL (`git@github.com:...`), token-based HTTPS auth is not applicable; the system falls back to system SSH key behavior.
- The `GET /settings` API returns the raw token value (consistent with existing OpenAI/Anthropic key behavior); the UI is responsible for masking it before display.

## Clarifications

### Session 2026-03-07

- Q: Should the GitHub token be returned as plain text from `GET /settings`, or omitted/redacted? → A: Return raw value — consistent with existing OpenAI/Anthropic API key behavior; UI masks for display.
- Q: Which branch should be cloned — default branch always, or user-specified per task? → A: User specifies an optional branch per task; if the branch doesn't exist on the remote, create it from the default branch.
- Q: Where should the GitHub token field appear in the Settings UI? → A: New dedicated **GitHub** section in Settings, separate from General and Agent sections.
