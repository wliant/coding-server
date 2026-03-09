# Feature Specification: Source Code Browser in Task Detail

**Feature Branch**: `010-source-code-browser`
**Created**: 2026-03-09
**Status**: Draft
**Input**: User description: "In Task Detail, if the task is completed, it would have source code generated. I want to be able to view the source code in the ui. it will be like a file browsing similar to github repository viewer - design the worker API to support this. - the web will call the worker api directly to support files browsing. - the file browsing should be in a separate tab in TaskDetail. the Download Code button will be moved to this tab."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse Generated Source Files (Priority: P1)

After a task completes, a developer navigates to the Task Detail page to inspect the generated source code. Below the existing task detail panel, they see the "Source Code" section with a file tree of all generated files. They click on any file to view its content in a code viewer with syntax highlighting.

**Why this priority**: This is the core value of the feature — allowing users to review generated code before downloading or pushing it. All other capabilities depend on the file browser being available.

**Independent Test**: Can be fully tested by completing a task and navigating to the Source Code tab; delivers full read-only code review capability.

**Acceptance Scenarios**:

1. **Given** a task with status `completed` or `failed`, **When** the user opens the Task Detail page, **Then** a "Source Code" section is rendered below the task detail panel containing a file tree listing all generated files and directories.
2. **Given** the file tree is displayed, **When** the user clicks a file name, **Then** the file's content appears in a viewer panel with syntax highlighting appropriate to the file extension.
3. **Given** the file tree is displayed, **When** the user clicks a directory, **Then** the directory expands or collapses to reveal or hide its children.
4. **Given** a task with status other than `completed` or `failed` (e.g., `pending`, `in_progress`, `cleaning_up`, `cleaned`), **When** the user views the Task Detail page, **Then** the "Source Code" section is not rendered.

---

### User Story 2 - Download Code from Source Code Tab (Priority: P2)

A developer has reviewed the generated source code and wants to download it as a zip archive. The "Download Code" button is available within the "Source Code" section alongside the file browser.

**Why this priority**: Download is a secondary action that follows code review; the file browser (P1) must exist first, and moving the button here keeps related actions co-located.

**Independent Test**: Can be tested by clicking "Download Code" within the Source Code tab and verifying the zip download is triggered.

**Acceptance Scenarios**:

1. **Given** the "Source Code" section is visible for a completed task, **When** the user clicks "Download Code", **Then** a zip archive of the working directory is downloaded to their machine.
2. **Given** the task is in a status other than `completed` or `failed`, **When** the user views the Task Detail page, **Then** the "Source Code" section (and with it the "Download Code" button) is not rendered.
3. **Given** the "Download Code" button exists, **When** the user views the main Task Detail panel, **Then** the "Download Code" button is no longer present there (it has moved to the Source Code tab).

---

### User Story 3 - Navigate Large File Trees (Priority: P3)

A developer working on a larger generated project wants to quickly locate a specific file. The file tree supports collapsible directories so the user can navigate a multi-level hierarchy without being overwhelmed.

**Why this priority**: Adds polish to the browsing experience but is not required for basic file viewing; the core feature remains valuable without deep tree navigation.

**Independent Test**: Can be tested by generating a task with nested directory output and verifying the tree renders hierarchically with expand/collapse controls.

**Acceptance Scenarios**:

1. **Given** the generated output contains nested directories, **When** the Source Code section is displayed, **Then** directories are shown as expandable nodes and files as leaf nodes.
2. **Given** a collapsed directory, **When** the user clicks the expand control, **Then** the directory's immediate children (files and subdirectories) become visible.
3. **Given** an expanded directory, **When** the user clicks the collapse control, **Then** its children are hidden.

---

### Edge Cases

- What happens when the working directory is empty (agent produced no files)?
- What happens when the worker is no longer available (task cleaned up or worker restarted) but the Source Code section is open? → The section displays an informative error; file endpoints rely on in-memory state only and return an error when state is absent.
- How does the system handle very large files (e.g., > 500 KB) — truncate with a warning or load on demand?
- What happens with binary files (images, compiled artifacts) — display a placeholder or omit from the viewer?
- What if a file path contains special characters or spaces?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The worker service MUST expose an endpoint that returns a recursive listing of all files and directories in the task's working directory, preserving the directory hierarchy.
- **FR-002**: The worker service MUST expose an endpoint that returns the raw text content of a single file identified by its relative path within the working directory.
- **FR-003**: The worker service MUST restrict file access to within the task's working directory; requests for paths that resolve outside the directory MUST be rejected with an error.
- **FR-004**: The Task Detail page MUST include a "Source Code" section rendered below the existing task detail panel (no tab reorganization of existing content); this section is shown when the task status is `completed` or `failed`.
- **FR-005**: The "Source Code" section MUST display a file tree matching the directory structure of the working directory, fetched directly from the worker service using the task's worker URL.
- **FR-006**: Selecting a file in the tree MUST display that file's content in a viewer panel with syntax highlighting based on the file extension.
- **FR-007**: The "Download Code" button MUST be relocated from the Task Detail panel to the "Source Code" section; it MUST no longer appear in the main detail panel, and MUST call the worker directly at the worker's download endpoint (not via the main API proxy).
- **FR-008**: The web frontend MUST call the worker's file listing and file content endpoints directly using the worker URL stored on the task record, without routing through the main API.
- **FR-009**: Binary files MUST be indicated in the file tree but MUST NOT be rendered as text in the viewer; a placeholder message ("Binary file — use Download to access") MUST be shown instead.
- **FR-010**: If the worker is unreachable or the working directory has been cleaned up, the Source Code section MUST display an informative error message rather than failing silently.
- **FR-011**: When the Source Code section first loads, the viewer panel MUST automatically display README.md if one exists at the root of the working directory; if no README.md is present, the first file encountered in the tree MUST be pre-selected and displayed.

### Key Entities

- **FileEntry**: Represents a node in the working directory tree — has a name, relative path, node type (file or directory), and for files an optional size in bytes.
- **FileTree**: The recursive structure of the working directory — a root `FileEntry` with nested children, returned by the file listing endpoint.
- **FileContent**: The text content of a single file identified by its relative path, along with metadata (size, detected content type or file extension).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can navigate from a completed task to viewing the first file's content in 0 additional clicks (auto-displayed on load); any other file in the tree requires 1 click.
- **SC-002**: The file tree renders within 2 seconds for working directories containing up to 200 files.
- **SC-003**: File content loads and displays within 1 second for files up to 100 KB.
- **SC-004**: The "Download Code" button is no longer present in the Task Detail panel for completed tasks; it appears exclusively in the Source Code tab.
- **SC-005**: All file browsing actions (list files, open a file) complete without errors against a live completed task in the development environment.

## Clarifications

### Session 2026-03-09

- Q: Does introducing "Source Code" as a tab require reorganizing existing task detail content into an "Overview" tab? → A: No — keep existing detail panel as-is; add "Source Code" as a separate section below it (no "Overview" tab created).
- Q: Should file listing/content endpoints reconstruct the path from disk after a worker restart, or rely on in-memory state only? → A: In-memory state only; return an error if the worker has restarted and state is gone.
- Q: Should the "Download Code" button call the worker directly or continue routing through the main API? → A: Call the worker directly at `{workerUrl}/download`, consistent with the Source Code section's direct-call pattern.
- Q: Should the Source Code section also render for `failed` tasks (agent may have generated partial output)? → A: Yes — show the section for both `completed` and `failed` tasks.
- Q: Should the viewer panel pre-select a file on load, or start empty? → A: Pre-select README.md if present, otherwise the first file in the tree; display its content immediately.

## Assumptions

- The task API response already includes `assigned_worker_url`; the web can use this field directly to call the worker without additional API changes.
- The worker's working directory persists until a cleanup (free) operation is triggered; file browsing is only relevant before cleanup.
- Text files are the primary artifact; syntax highlighting covers common programming languages (Python, TypeScript, JavaScript, JSON, YAML, Markdown, shell scripts, etc.).
- Files larger than 500 KB display a truncated preview or a "file too large" notice rather than being fetched in full automatically.
- The feature targets tasks whose `assigned_worker_url` is set; tasks without a worker URL (pre-010 completed tasks) show an appropriate unavailable message in the Source Code tab.
