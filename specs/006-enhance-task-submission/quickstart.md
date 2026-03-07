# Quickstart: Enhanced Task Submission

**Feature**: 006-enhance-task-submission
**Date**: 2026-03-06

This document describes the three integration scenarios that validate the complete feature. Each scenario is independently testable.

---

## Scenario 1: Submit a Task for a New Project (US1)

**Goal**: Create a new project and queue a task in a single form submission.

### Prerequisites
- At least one active agent exists in the registry (seeded by migration 0005).
- The task submission form is open (`/tasks/new`).

### Happy Path

1. Open the task submission form.
2. The Project dropdown shows "New Project" plus any existing projects.
3. Select **"New Project"**.
4. A **Project Name** text field appears. Enter a name (e.g., "My App").
5. A **Git URL** field is visible but marked optional. Leave it blank.
6. The **Agent** dropdown is populated from `GET /agents`. Select an agent.
7. Enter requirements text.
8. Click **Submit Task**.

**Expected API call**:
```json
POST /tasks
{
  "project_type": "new",
  "project_name": "My App",
  "agent_id": "<uuid-of-selected-agent>",
  "requirements": "Build a simple REST API"
}
```

**Expected response (201)**:
```json
{
  "id": "<task-uuid>",
  "project": { "id": "<project-uuid>", "name": "My App", "source_type": "new" },
  "agent": { "id": "<agent-uuid>", "identifier": "spec_driven_development", "display_name": "Spec-Driven Development" },
  "requirements": "Build a simple REST API",
  "status": "pending",
  ...
}
```

**Verification**: Task appears in task list with status `pending` and project name "My App".

### Validation Failure: Missing Project Name

1. Select "New Project", leave Project Name blank, fill in agent and requirements.
2. Click Submit.

**Expected**: Submission is blocked with an inline error: "Project name is required for new projects."

### Validation Failure: Missing Agent

1. Select "New Project", fill in Project Name and requirements, do not select an agent.
2. Click Submit.

**Expected**: Submit button is disabled or shows inline error: "Agent is required."

---

## Scenario 2: Submit a Task for an Existing Project (US2)

**Goal**: Queue a new task against an existing project. Git URL is required.

### Prerequisites
- At least one project exists (created in Scenario 1 or pre-seeded).
- That project has a git URL stored (or we test the empty-URL case separately).

### Happy Path

1. Open the task submission form.
2. Select an **existing project** from the dropdown (projects are listed alongside "New Project").
3. The **Project Name** field disappears (not applicable for existing projects).
4. The **Git URL** field is pre-populated with the project's stored `git_url` and marked as required.
5. Select an agent and enter requirements.
6. Click **Submit Task**.

**Expected API call**:
```json
POST /tasks
{
  "project_type": "existing",
  "project_id": "<existing-project-uuid>",
  "agent_id": "<uuid-of-selected-agent>",
  "git_url": "https://github.com/org/repo",
  "requirements": "Add user authentication"
}
```

**Expected response (201)**: Task linked to the existing project, status `pending`.

### Edge Case: Existing Project with No Stored Git URL

1. Select an existing project that has no `git_url` stored.
2. The Git URL field is empty and required.
3. Attempt to submit without filling it in.

**Expected**: Submission blocked with inline error: "Git URL is required for existing projects."

### Edge Case: Projects with Same Name

- If two projects share the same name, the dropdown shows both entries, each displaying the name alongside its creation date.
- Selection sets `project_id` to the chosen entry's UUID.

---

## Scenario 3: Add Git URL to a Completed Task and Push (US3)

**Goal**: A user who submitted a new-project task without a git URL can later add a URL and push the generated code.

### Prerequisites
- A task for a new project exists with status `completed`.
- The project has no stored `git_url`.

### Happy Path

1. Navigate to the completed task's detail page (`/tasks/<task-id>`).
2. The page shows a **Git URL** input field (empty) and a **Push to Remote** button.
3. Enter a valid git URL (e.g., `https://github.com/org/new-repo`).
4. Click **Push to Remote**.

**Expected API call**:
```json
POST /tasks/<task-id>/push
{
  "git_url": "https://github.com/org/new-repo"
}
```

**Expected response (200)**:
```json
{
  "branch_name": "task/<short-id>",
  "remote_url": "https://github.com/org/new-repo",
  "pushed_at": "2026-03-06T12:00:00Z"
}
```

**Side effect**: The project's `git_url` is saved to `projects.git_url`. On subsequent visits to the task detail, the URL field is pre-populated.

### Case: Task Already Has a Stored Git URL

1. Navigate to the completed task's detail page.
2. The Git URL field is pre-populated with the project's stored URL.
3. The Push to Remote button is immediately available (no URL entry needed).
4. Click Push to Remote (no body required, or body with `git_url` omitted).

**Expected API call**: `POST /tasks/<task-id>/push` with empty body or no body.

### Validation: Malformed Git URL

1. Enter a URL that does not start with `https://` or `git@` (e.g., `ftp://invalid`).

**Expected**: Inline validation error before the form submits: "Git URL must start with https:// or git@."

---

## API Sequence Diagrams

### New Project Task Submission

```
UI                         API                        DB
│                          │                          │
│── GET /agents ──────────►│                          │
│◄─ [AgentResponse] ───────│── SELECT agents ────────►│
│                          │◄─ rows ──────────────────│
│                          │                          │
│── POST /tasks ──────────►│                          │
│  {project_type:"new",    │── INSERT projects ──────►│
│   project_name:"My App", │── INSERT jobs ──────────►│
│   agent_id:"...",        │◄─ job+project ───────────│
│   requirements:"..."}    │                          │
│◄─ TaskResponse (201) ────│                          │
```

### Push with Git URL (US3)

```
UI                         API                        DB         Git Remote
│                          │                          │          │
│── POST /tasks/{id}/push ►│                          │          │
│  {git_url:"https://..."} │── UPDATE projects ──────►│          │
│                          │   SET git_url=...        │          │
│                          │◄─ ok ────────────────────│          │
│                          │── git push ─────────────────────────►│
│                          │◄─ success ───────────────────────────│
│◄─ PushResponse (200) ────│                          │          │
```
