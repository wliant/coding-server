# Feature Specification: Cross-Platform Build Tool

**Feature Branch**: `003-cross-platform-build`
**Created**: 2026-03-03
**Status**: Draft
**Input**: User description: "this project uses makefile for building. use some other tools that is very friendly for windows and mac development environment and also suitable for this project"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer on Windows Runs Project Commands (Priority: P1)

A developer using Windows opens a terminal (PowerShell, Command Prompt, or Windows Terminal) and runs the same commands they would have run with `make dev`, `make test-all`, etc. — without needing WSL, GNU Make, or any Unix-specific tooling. The commands work natively.

**Why this priority**: The primary motivation for this change is Windows compatibility. Without this, Windows developers cannot participate without workarounds such as WSL, which adds friction and inconsistency.

**Independent Test**: Can be fully tested on a clean Windows machine by installing the new tool, running `task dev`, and confirming the Docker Compose dev environment starts correctly.

**Acceptance Scenarios**:

1. **Given** a Windows developer has installed the new task runner, **When** they run `task dev` in the project root, **Then** the Docker Compose development environment starts with hot-reload, identical to the previous `make dev` behavior.
2. **Given** a Windows developer runs `task test-all`, **When** all services are running, **Then** all test suites (API, worker, tools, web) execute and report results.
3. **Given** a developer with no Unix tools installed runs `task --list`, **When** the command executes, **Then** all available tasks and their descriptions are listed clearly.

---

### User Story 2 - Developer on macOS Runs Project Commands (Priority: P2)

A developer using macOS uses the new task runner in place of `make`. The experience is consistent with the Windows developer's experience and does not require separate documentation or special flags.

**Why this priority**: macOS already supports Make, but adopting a unified cross-platform tool ensures all developers share identical commands, documentation, and behavior regardless of OS.

**Independent Test**: Can be tested on a macOS machine by installing the new tool and running `task generate` to confirm OpenAPI spec export and TypeScript client regeneration work correctly.

**Acceptance Scenarios**:

1. **Given** a macOS developer installs the new task runner, **When** they run `task generate`, **Then** the OpenAPI spec is exported and the TypeScript client is regenerated.
2. **Given** a macOS developer runs `task e2e`, **Then** the end-to-end test suite runs in isolation and exits with the correct exit code (pass/fail).

---

### User Story 3 - Developer Discovers Available Commands (Priority: P3)

A developer new to the project wants to understand what commands are available without reading the README or Makefile. They run a single help command and get a list of all tasks with descriptions.

**Why this priority**: Discoverability reduces onboarding time. This was already supported via `make help`; the replacement must preserve or improve this.

**Independent Test**: Tested by running `task --list` and confirming all task names and one-line descriptions are printed.

**Acceptance Scenarios**:

1. **Given** a developer in the project root, **When** they run `task --list`, **Then** all available tasks are printed with descriptions.
2. **Given** a developer asks for help on a specific task, **When** they run `task --summary <task-name>`, **Then** that task's description and commands are shown.

---

### User Story 4 - CI/CD Pipeline Uses the New Task Runner (Priority: P3)

Continuous integration pipelines currently call `make` targets. After the migration, CI configuration is updated to call the new tool with identical target names, preserving existing pipeline behavior.

**Why this priority**: Ensures the migration does not break automated testing or deployment pipelines.

**Independent Test**: CI pipeline configuration is updated and a pipeline run completes with the same pass/fail outcomes as before the migration.

**Acceptance Scenarios**:

1. **Given** the CI configuration references `task test-all`, **When** CI runs on a push, **Then** all test suites execute and results are reported correctly.

---

### Edge Cases

- What happens when a developer runs a task before the Docker Compose environment is started? The task should fail with a clear, descriptive error message.
- What happens if the task runner binary is not installed? The developer should see a clear, actionable error (not a cryptic shell error), and the README must link to installation instructions.
- What if a task fails mid-execution (e.g., `test-all` partially completes)? The tool must exit with a non-zero exit code so CI correctly detects failure.
- What if the project is cloned on a new machine without the task runner? The `README.md` must include one-command installation instructions for Windows and macOS.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST provide native Windows support without requiring WSL, Cygwin, or GNU Make. Windows compatibility is achieved by keeping all bash-dependent script execution inside Docker containers; the task runner itself only issues `docker compose` commands on the host.
- **FR-002**: The tool MUST provide native macOS and Linux support, installable via standard package managers (e.g., Homebrew on macOS, apt/snap/binary download on Linux).
- **FR-003**: The tool MUST support exactly the 15 existing Makefile targets: `dev`, `dev-down`, `e2e`, `prod`, `prod-down`, `generate`, `test-api`, `test-worker`, `test-tools`, `test-web`, `test-all`, `lint-api`, `logs`, `shell-api`, `check-openapi`, and `help`/`--list`. No new tasks are added as part of this feature.
- **FR-004**: The tool MUST support task dependencies (e.g., `test-all` depends on individual test targets).
- **FR-005**: The tool MUST support a list/help command that prints all available tasks with their descriptions in a single invocation.
- **FR-006**: The tool MUST support referencing environment variables from `.env` and `.env.e2e` files, consistent with the current Docker Compose usage.
- **FR-007**: The tool MUST be installable as a single binary or via a standard package manager with no additional runtime dependencies.
- **FR-008**: The tool MUST propagate exit codes, so failed tasks exit with non-zero exit codes for CI compatibility.
- **FR-009**: The existing `Makefile` MUST be deleted as the final step of this feature, once all tasks are verified working in the new task runner. No transition period with both files coexisting is required.
- **FR-010**: The `CLAUDE.md` project instructions and `README` MUST be updated to replace all `make <target>` references with the new command equivalents. The `README` MUST also document shell auto-completion setup (bash, zsh, fish, PowerShell) as a recommended optional step for developers who want it.

### Key Entities

- **Task Definition File**: The configuration file (e.g., `Taskfile.yml`) replacing the Makefile, located in the project root. Defines all project tasks, their shell commands, dependencies, descriptions, and environment handling.
- **Task**: A named, runnable unit of work with a description, one or more shell commands, and optional dependencies on other tasks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer on a fresh Windows machine can install the task runner and run `task dev` in under 5 minutes from cloning the repository, with no additional Unix tooling required.
- **SC-002**: All 15 existing Makefile targets are available and functionally identical under the new task runner.
- **SC-003**: The list command outputs all available task names and descriptions in a single command invocation on both Windows and macOS.
- **SC-004**: CI pipelines continue to pass after migrating from `make` to the new tool, with no new test failures introduced.
- **SC-005**: Developers on Windows, macOS, and Linux can all install the task runner and use identical `task <target>` commands with no OS-specific flags or workarounds.

## Assumptions

- The project's Docker Compose-based workflow remains unchanged; the task runner wraps existing Docker Compose commands rather than replacing them.
- The task runner acts as a **thin orchestration layer**: all bash-dependent commands (e.g., `api/scripts/check_openapi_fresh.sh`) execute inside Docker containers where bash is already available. The task runner itself only issues `docker compose` calls and does not invoke shell scripts directly on the host. This is how Windows native compatibility is achieved — no shell scripts run on the host OS.
- Developers are expected to have Docker Desktop installed on both Windows and macOS (this is an existing requirement, not introduced by this feature).
- The chosen tool is **Taskfile (go-task)** — a YAML-based, cross-platform task runner with a single-binary distribution, widely adopted as a Make alternative. It supports Windows, macOS (via Homebrew), and Linux (via apt, snap, or direct binary download) as first-class platforms.
- The CI environment (e.g., GitHub Actions runners) supports installing the task runner binary via a setup action or shell command; no special runner image changes are needed.
- The `Makefile` is deleted as the final step of this feature once all task equivalents are verified. No transition period or dual-maintenance window is needed.

## Clarifications

### Session 2026-03-03

- Q: How should bash script dependencies in task commands be handled to achieve true Windows compatibility? → A: All bash-dependent commands run inside Docker containers; the task runner only issues `docker compose` calls on the host — no host-level shell scripts required.
- Q: Is Makefile deletion in-scope for this feature? → A: Yes — the Makefile is deleted as the final step once all tasks are verified working in the new task runner; no transition period required.
- Q: Should Linux-host developers be a first-class supported platform alongside Windows and macOS? → A: Yes — Linux is a supported platform; installation instructions cover Windows, macOS, and Linux.
- Q: Should the Taskfile include new tasks beyond the 15 existing Makefile targets? → A: No — strict 1:1 migration only; exactly 15 existing targets, no additions.
- Q: Should shell auto-completion setup be included in the README installation instructions? → A: Optional — documented as a recommended optional step, not mandatory.
