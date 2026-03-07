# Feature Specification: Enhanced Task Submission

**Feature Branch**: `006-enhance-task-submission`
**Created**: 2026-03-06
**Status**: Draft
**Input**: User description: "Enhance task submission: project selection (new/existing), project naming, git URL field, single agent selector"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Submit Task for a New Project (Priority: P1)

A user wants to kick off work on a brand-new codebase that does not yet exist in the system. They open the task submission form, choose to create a new project, give the project a name, optionally provide a git repository URL, select an agent, enter their requirements, and submit. The system creates a new project record and queues the task.

**Why this priority**: This is the primary submission path for new work and the most common scenario. All other stories build on this foundation.

**Independent Test**: Can be fully tested by submitting a task with "New Project" selected, providing a name and requirements (no git URL), and verifying the task appears in the task list with the correct project name and Pending status.

**Acceptance Scenarios**:

1. **Given** the task submission form is open, **When** the user selects "New Project", **Then** a Project Name field appears and the Git URL field is shown but not required.
2. **Given** the user has entered a project name and requirements, **When** they submit the form, **Then** a new project is created with the given name and a task is queued with Pending status.
3. **Given** the user selects "New Project" but leaves the Project Name blank, **When** they attempt to submit, **Then** submission is blocked and a validation message indicates the project name is required.
4. **Given** the user selects "New Project" and optionally enters a git URL, **When** they submit, **Then** the URL is saved with the project and the form submits successfully.

---

### User Story 2 - Submit Task for an Existing Project (Priority: P2)

A user wants to queue additional work on a project already in the system. They open the task submission form, select an existing project from the list, confirm or update its git URL (which is required), choose an agent, enter requirements, and submit.

**Why this priority**: Existing-project submissions connect new requirements to tracked projects and enable incremental delivery — critical for ongoing work.

**Independent Test**: Can be fully tested by selecting an existing project, confirming the git URL is pre-populated and required, submitting requirements, and verifying the task is created linked to the correct project.

**Acceptance Scenarios**:

1. **Given** at least one project exists in the system, **When** the user opens the task submission form, **Then** the Project field lists all existing projects alongside a "New Project" option.
2. **Given** the user selects an existing project, **When** the form loads, **Then** the Git URL field is pre-populated with the project's stored URL and is marked as required.
3. **Given** the user selects an existing project but clears the Git URL, **When** they attempt to submit, **Then** submission is blocked and a message indicates the git URL is required for existing projects.
4. **Given** the user selects an existing project with a valid git URL, **When** they submit requirements, **Then** a task is created and linked to that project.

---

### User Story 3 - Add Git URL and Push a Completed New-Project Task (Priority: P3)

After a task for a new project completes, the user who did not provide a git URL at submission time can navigate to the completed task, add a git URL to the project, and trigger a push of the generated code to that repository.

**Why this priority**: Closes the loop for the new-project workflow — users can defer the git URL until they are ready to publish the generated code, without needing to resubmit.

**Independent Test**: Can be fully tested by completing a new-project task without a git URL, then navigating to the task detail page, entering a URL, clicking Push to Remote, and verifying the push succeeds.

**Acceptance Scenarios**:

1. **Given** a completed task for a new project has no git URL, **When** the user views the task detail page, **Then** a field to enter a git URL and a Push to Remote action are both displayed.
2. **Given** the user enters a valid git URL and clicks Push to Remote, **Then** the system saves the URL to the project and pushes the work directory to the repository.
3. **Given** a completed task for a new project already has a git URL stored, **When** the user views the task detail page, **Then** the existing URL is shown pre-filled and Push to Remote is immediately available.

---

### Edge Cases

- What happens when an existing project has no stored git URL (data created before this feature)? The Git URL field is shown empty and treated as required before the task can be submitted.
- What if only one agent option is available in the system? The Agent field still appears and defaults to that single option; the user can confirm or change it if more options are added later.
- What if the user enters a malformed git URL? A clear inline validation error is shown before the form can be submitted or a push triggered.
- What if no existing projects exist yet? The Project dropdown shows only the "New Project" option and the existing-project selection path is simply not offered.
- What if multiple projects share the same name? The Project dropdown displays all matching projects; each entry shows the project name alongside its creation date to help the user distinguish between them.
- What if two tasks for the same project are submitted simultaneously? Each task is independent; the project record is shared but tasks are queued separately.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The task submission form MUST provide a Project field offering both a "New Project" creation option and a list of all existing projects.
- **FR-002**: When "New Project" is selected, the form MUST display a required Project Name field; this field MUST NOT appear when an existing project is selected. Project names do not need to be unique — two projects may share the same name and are distinguished by their system-assigned identifier.
- **FR-003**: The task submission form MUST always display a Git Repository URL field, visible for both new and existing project selections.
- **FR-004**: For existing projects, the Git Repository URL field MUST be pre-populated with the project's stored URL and MUST be required before submission is allowed.
- **FR-005**: For new projects, the Git Repository URL field MUST be optional; submission MUST succeed without it.
- **FR-006**: The task submission form MUST replace the separate Dev Agent and Test Agent fields with a single Agent field. Existing tasks that have legacy dual-agent data are unaffected — those fields are deprecated and no data migration is required.
- **FR-007**: The Agent field MUST list all agents from the system's agent registry and MUST require a selection before submission is permitted. The registry is database-backed; agents can be added or removed without a code deploy.
- **FR-008**: On the task detail page for a completed task belonging to a project without a git URL, users MUST be able to enter a git URL and trigger a push to that repository.
- **FR-009**: The system MUST validate all required fields inline and prevent submission if any required field is missing, displaying a specific message per field.
- **FR-010**: When an existing project is selected, the system MUST pre-populate the Git URL field from the stored project record.

### Key Entities

- **Project**: Represents a codebase being developed. Key attributes: name (required), git repository URL (optional at creation), status, creation date. A project may have many tasks over its lifetime.
- **Task**: Represents a unit of work submitted by a user. Key attributes: requirements, chosen agent, status, linked project, timestamps. A task belongs to exactly one project.
- **Agent**: Represents an available agent library the system can invoke. Stored in a database registry table. Key attributes: identifier (used internally to resolve the library), display name (shown to the user), active status. The selected agent determines which automation library executes the requirements.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete task submission for either a new or existing project in under 2 minutes from opening the form to receiving confirmation of a queued task.
- **SC-002**: 100% of existing-project task submissions require a git URL — the system must not allow submission without one.
- **SC-003**: Users can add a git URL to a completed new-project task and initiate a repository push without resubmitting or recreating the task.
- **SC-004**: The consolidated single Agent field reduces the number of required agent-related selections from two fields to one for every task submission.
- **SC-005**: All validation errors are surfaced inline on the form without a page reload, so users see exactly which fields need attention before re-submitting.

## Clarifications

### Session 2026-03-06

- Q: When the two agent fields are consolidated into one, what happens to existing tasks that already have both fields stored? → A: Deprecate old fields — no migration. Existing tasks keep their stored `dev_agent_type`/`test_agent_type` data as-is; the old columns are ignored in the UI going forward. New tasks use a single `agent` field only.
- Q: Where does the list of available agents come from? → A: Database-backed registry — agents are stored as rows in a dedicated table. Admins can add or remove agents without a code deploy. The Agent field on the task submission form is populated from this table at runtime.
- Q: Must project names be unique system-wide? → A: No — duplicate project names are allowed. Projects are distinguished by their internal ID, not their name.

## Assumptions

- The list of available agents is sourced from a database-backed agent registry table. New agents are added by inserting a row into this table; no code deployment is required. The Agent field on the submission form is populated from this table at runtime.
- Git URL format validation accepts URLs beginning with `https://` or `git@`; other formats are rejected with a clear message.
- Existing projects are all projects currently stored in the system; no separate filtering or archiving is in scope.
- The "Push to Remote" behaviour on the task detail page is unchanged from feature 005 — only the ability to add a git URL on that page is new.
- A project's name cannot be changed after creation through this form (renaming is out of scope for this feature).
- The single Agent field maps to the same underlying concept as the previous agent fields; the system will use the selected agent library for the full task execution.
