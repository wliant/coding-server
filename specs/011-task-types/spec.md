# Feature Specification: Task Types

**Feature Branch**: `b2`
**Created**: 2026-03-11
**Status**: Complete

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Submit Tasks of Different Types (Priority: P1)

A developer wants to submit different kinds of tasks (build a feature, fix a bug, review code, refactor, write tests, scaffold a new project). They open the Submit Task form and select the appropriate task type from a dropdown. The form dynamically adjusts to show relevant fields: scaffold tasks require a project name, non-scaffold tasks require a git URL, review tasks require a branch and optionally accept a commits-to-review count.

**Why this priority**: This is the core interaction - users must be able to specify what kind of work they want done. All downstream behaviour (validation, display, agent instructions) depends on the task type being set correctly.

**Acceptance Scenarios**:

1. **Given** the user navigates to `/tasks/new`, **When** the page loads, **Then** a "Task Type" dropdown is displayed with 6 options: Build a Feature, Fix a Bug, Review Code, Refactor Code, Write Tests, Scaffold a Project.
2. **Given** the user selects "Scaffold a Project", **When** the form updates, **Then** a "Project Name" field appears (required) and the "Git URL" field becomes optional.
3. **Given** the user selects "Review Code", **When** the form updates, **Then** the "Branch" field becomes required and a "Commits to Review" field appears (optional).
4. **Given** the user selects any non-scaffold type, **When** the form updates, **Then** the "Git URL" field is required and no "Project Name" field is shown.

---

### User Story 2 - View Task Type in List and Detail Pages (Priority: P2)

A developer views the task list and can immediately see what type each task is via a badge. On the task detail page, the task type is displayed alongside other metadata.

**Why this priority**: Visibility of task type helps users quickly identify and manage their tasks; depends on task type being stored (P1).

**Acceptance Scenarios**:

1. **Given** tasks exist with different types, **When** the user views `/tasks`, **Then** each task row displays a badge showing the task type label.
2. **Given** a task exists, **When** the user views `/tasks/{id}`, **Then** the task type is displayed in the detail metadata.

---

### User Story 3 - Validation Enforcement (Priority: P2)

The API enforces type-specific validation rules to prevent invalid task submissions.

**Why this priority**: Ensures data integrity; depends on the task type field (P1) being available.

**Acceptance Scenarios**:

1. **Given** a POST to `/tasks` with `task_type: "scaffold_project"` and no `project_name`, **When** the request is processed, **Then** a 422 error is returned.
2. **Given** a POST to `/tasks` with `task_type: "build_feature"` and no `git_url`, **When** the request is processed, **Then** a 422 error is returned.
3. **Given** a POST to `/tasks` with `task_type: "review_code"` and no `branch`, **When** the request is processed, **Then** a 422 error is returned.
4. **Given** a POST to `/tasks` with `task_type: "build_feature"` and `commits_to_review` set, **When** the request is processed, **Then** a 422 error is returned (commits_to_review only valid for review_code).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `jobs` table MUST have a `task_type` column (VARCHAR(30), NOT NULL, default `build_feature`).
- **FR-002**: The `jobs` table MUST have a `commits_to_review` column (INTEGER, nullable).
- **FR-003**: Migration `0011_add_task_type_to_jobs.py` MUST backfill existing rows: `scaffold_project` for jobs linked to `source_type = 'new'` projects, `build_feature` for the rest.
- **FR-004**: The API MUST define a `TaskType` enum with values: `build_feature`, `fix_bug`, `review_code`, `refactor_code`, `write_tests`, `scaffold_project`.
- **FR-005**: `CreateTaskRequest` MUST accept `task_type` (required, replacing the old `project_type` field) along with optional `commits_to_review`.
- **FR-006**: Cross-field validation: `scaffold_project` requires `project_name`; non-scaffold types require `git_url`; `review_code` requires `branch`; `commits_to_review` only valid for `review_code`.
- **FR-007**: `TaskResponse` MUST include `task_type` as a string field.
- **FR-008**: `TaskDetailResponse` MUST include `task_type` and `commits_to_review` fields.
- **FR-009**: The agents-controller MUST pass `task_type` and `commits_to_review` through the work payload when delegating to workers.
- **FR-010**: The worker MUST accept and store `task_type` and `commits_to_review` from the work payload.
- **FR-011**: The frontend task form MUST display a "Task Type" dropdown with 6 options and conditionally show/hide fields based on the selected type.
- **FR-012**: The frontend task list MUST display a task type badge for each task; the task detail page MUST show the task type.

### Key Entities

- **TaskType**: Enum (`build_feature`, `fix_bug`, `review_code`, `refactor_code`, `write_tests`, `scaffold_project`) defining the kind of work a task represents.
- **Job.task_type**: Column storing the task type on each job record.
- **Job.commits_to_review**: Optional integer column for review_code tasks specifying how many recent commits to review.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 6 task types can be submitted via the API and are persisted correctly in the database.
- **SC-002**: Cross-field validation rejects invalid combinations (scaffold without project_name, non-scaffold without git_url, review without branch, commits_to_review on non-review) with 422 responses.
- **SC-003**: The task list API response includes `task_type` for every task.
- **SC-004**: The task detail API response includes both `task_type` and `commits_to_review`.
- **SC-005**: The frontend form dynamically adjusts fields based on selected task type and displays type badges in the task list.

## Migration

- `api/alembic/versions/0011_add_task_type_to_jobs.py`: Adds `task_type` (VARCHAR(30)) and `commits_to_review` (INTEGER) columns to `jobs` table. Backfills existing data based on project source_type.
