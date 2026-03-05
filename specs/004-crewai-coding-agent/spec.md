# Feature Specification: CrewAI Coding Agent Module

**Feature Branch**: `004-crewai-coding-agent`
**Created**: 2026-03-04
**Status**: Draft
**Input**: User description: "Create a simple_crewai_coding_agent module. it should use uv for package management, use crewai, define the necessary agents required to perform coding. the crewai agents should be using Ollama by default, but it should be configurable. when starting the agent, it should be given the working directory, the requirement, project name. Use pytests in the project. create test to test a simple coding task. Out of scope: UI and api changes. Out of scope: After pytests is created, no need to execute it. Let human configure the llm"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Coding Agent on a Task (Priority: P1)

A developer invokes the coding agent module with a working directory, project name, and natural-language requirement. The agent autonomously generates the required source code and writes it to the specified working directory.

**Why this priority**: This is the core value of the module — a working end-to-end coding task execution. All other stories build on this foundation.

**Independent Test**: Can be fully tested by invoking the agent's entry point with a simple coding requirement (e.g., "write a Python function that adds two numbers") and verifying the output file is created in the target directory.

**Acceptance Scenarios**:

1. **Given** a valid working directory, project name, and a coding requirement, **When** the agent is started, **Then** it produces source code in the working directory that satisfies the requirement.
2. **Given** a working directory that does not yet exist, **When** the agent is started, **Then** it creates the directory and still produces the output.
3. **Given** a requirement that is clearly stated, **When** the agent completes, **Then** the generated code is syntactically correct and runnable.

---

### User Story 2 - Configure the Language Model Provider (Priority: P2)

A developer configures which language model backend the agents use. By default, Ollama is used with a sensible local model, but the developer can point the module to any compatible backend by changing configuration (environment variable or config argument) before running.

**Why this priority**: The module must be portable across environments (local with Ollama, cloud with another provider). Hardcoding an LLM defeats this purpose.

**Independent Test**: Can be tested by changing the LLM configuration value and verifying the agent connects to the specified provider without code changes.

**Acceptance Scenarios**:

1. **Given** no LLM configuration is provided, **When** the agent starts, **Then** it connects to Ollama with a default model.
2. **Given** a custom LLM configuration is provided, **When** the agent starts, **Then** it uses the specified provider and model instead of the default.
3. **Given** an invalid LLM configuration, **When** the agent starts, **Then** it raises a clear, descriptive error before attempting to run the task.

---

### User Story 3 - Automated Test Validates Agent Behaviour (Priority: P3)

A developer runs the pytest suite for the module and at least one test exercises a simple end-to-end coding task using the agent, verifying the expected output is produced.

**Why this priority**: Ensures the module's behaviour is verifiable in CI and during development without a human needing to inspect outputs manually. Marked P3 because it depends on the core agent (P1) being in place.

**Independent Test**: Can be fully tested by running `pytest` from the module root and observing the coding-task test pass (the test itself is not executed in CI by default, per scope — it is defined and runnable by humans who have configured an LLM).

**Acceptance Scenarios**:

1. **Given** the module's test suite is present and an LLM is configured, **When** the coding-task test is run, **Then** it passes and the generated code satisfies the requirement described in the test.
2. **Given** the test file exists, **When** it is inspected, **Then** it covers at least one concrete coding requirement (e.g., "write a function that adds two numbers") and asserts on the produced output.

---

### Edge Cases

- What happens when the working directory path contains spaces or special characters?
- What happens when the Ollama service is unreachable and no fallback is configured?
- What happens when the requirement string is empty or contains only whitespace?
- What happens when the working directory is read-only and the agent cannot write output?
- How does the module behave if the LLM returns code with syntax errors — does it retry or surface the error?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The module MUST be a self-contained Python package (`simple_crewai_coding_agent`) with its own dependency management via `uv`.
- **FR-002**: The module MUST define a CrewAI crew composed of at minimum two agents: a **Coder** agent (responsible for writing code) and a **Reviewer** agent (responsible for reviewing and validating the code for correctness).
- **FR-003**: The module MUST expose a programmatic entry point that accepts three required inputs: `working_directory` (path), `project_name` (string), and `requirement` (string).
- **FR-004**: The module MUST write the agent-generated code output to a file within the specified `working_directory`.
- **FR-005**: The LLM provider and model used by CrewAI agents MUST default to Ollama with a documented default model name.
- **FR-006**: The LLM provider and model MUST be configurable without modifying source code — via environment variables or a configuration argument at invocation time.
- **FR-007**: The module MUST include a pytest-based test suite with at least one test that exercises a complete coding task (e.g., generating a simple utility function), asserting the output exists and meets basic quality criteria (e.g., file is non-empty, contains valid Python syntax).
- **FR-008**: The module MUST use `uv` as the package manager (`pyproject.toml` with `[tool.uv]` or equivalent uv-compatible layout).
- **FR-009**: The module MUST NOT introduce changes to the web UI or API components of the broader project.

### Key Entities

- **Crew**: The top-level orchestrator that sequences agent execution for a given coding task. Receives `working_directory`, `project_name`, and `requirement` as inputs.
- **Coder Agent**: A CrewAI agent tasked with producing source code that fulfils the given requirement. Writes output to the working directory.
- **Reviewer Agent**: A CrewAI agent tasked with reviewing the Coder's output for correctness, clarity, and completeness. May request revisions.
- **LLM Configuration**: A runtime-configurable value specifying the backend provider and model name used by all agents. Defaults to Ollama.
- **Task**: A unit of work assigned to an agent within the crew (CrewAI concept). At minimum: a "write code" task and a "review code" task.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can start the coding agent from scratch (fresh checkout, `uv sync`) and run a coding task within 5 minutes, without manual dependency installation steps beyond `uv sync`.
- **SC-002**: Given a requirement to "write a Python function that adds two numbers", the agent produces a non-empty Python file in the specified working directory that contains a syntactically valid function.
- **SC-003**: Switching the LLM from the default Ollama to a different provider requires only a configuration change (environment variable or argument), with no edits to module source files.
- **SC-004**: All pytest tests in the module are collected and executed without errors when an LLM is properly configured, and the coding-task test passes.
- **SC-005**: The module's public entry point is documented sufficiently (inline or in a README section) that a developer unfamiliar with CrewAI can invoke it correctly on first attempt.

## Assumptions

- The host machine where the agent runs has Ollama installed and a compatible model (e.g., `codellama` or `llama3`) already pulled.
- The module is a standalone package under a new top-level directory (e.g., `simple_crewai_coding_agent/`) within the monorepo, not integrated into `api/`, `worker/`, or `tools/`.
- "Configurable LLM" means the developer sets an environment variable or passes a config object/argument before invoking the crew — the module does not need a configuration file on disk.
- The pytest test for the coding task is written and can be run by a human; it is not required to run in CI (no automated execution is in scope).
- The Reviewer agent does not need to auto-iterate corrections in a loop beyond what CrewAI's default task sequencing supports.
- Output format of the generated code is a plain text file (e.g., `.py`); no specific filename convention is mandated beyond residing in `working_directory`.
