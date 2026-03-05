# Data Model: CrewAI Coding Agent Module

**Phase**: Phase 1 — Design
**Feature**: 004-crewai-coding-agent
**Date**: 2026-03-04

---

## Overview

This module has no persistent database. All entities are in-memory Python objects created at invocation time and discarded when the crew run completes. The "data model" describes the runtime object graph and the inputs/outputs of the public entry point.

---

## Runtime Entities

### `CodingCrew`

Top-level orchestrator that assembles agents and tasks and drives execution.

| Field | Type | Description |
|---|---|---|
| `working_directory` | `Path` | Absolute path where generated code is written |
| `project_name` | `str` | Human-readable name for the coding project |
| `requirement` | `str` | Natural-language description of what to build |
| `llm` | `crewai.LLM` | Configured language model instance |
| `_crew` | `crewai.Crew` | Internal CrewAI Crew object (not public) |

**Validation rules**:
- `working_directory` must be a valid filesystem path (created if absent)
- `requirement` must be non-empty string (strip whitespace check)
- `project_name` must be non-empty string

---

### `CoderAgent`

CrewAI Agent responsible for writing source code.

| Attribute | Value |
|---|---|
| Role | `"Senior Python Developer"` |
| Goal | Write clean, functional Python code satisfying the requirement |
| Backstory | Experienced Python developer focused on clean, testable code |
| `allow_code_execution` | `False` (no sandboxed execution — output is text) |
| `max_retry_limit` | `3` |
| LLM | Shared `crewai.LLM` instance from `make_llm()` |

---

### `ReviewerAgent`

CrewAI Agent responsible for reviewing the Coder's output for correctness and quality.

| Attribute | Value |
|---|---|
| Role | `"Code Reviewer"` |
| Goal | Identify issues, correctness problems, and suggest improvements |
| Backstory | Senior engineer specialising in Python code quality and best practices |
| `allow_code_execution` | `False` |
| LLM | Shared `crewai.LLM` instance from `make_llm()` |

---

### `CodingTask`

CrewAI Task assigned to `CoderAgent`.

| Field | Value |
|---|---|
| `description` | `"Implement the following requirement in Python: {requirement}"` |
| `expected_output` | A complete Python module with inline comments |
| `output_file` | `{working_directory}/{project_name}.py` |
| `agent` | `CoderAgent` |

---

### `ReviewTask`

CrewAI Task assigned to `ReviewerAgent`.

| Field | Value |
|---|---|
| `description` | `"Review the implementation for correctness, style, edge cases, and adherence to the requirement."` |
| `expected_output` | A code review report summarising findings and any recommended improvements |
| `context` | `[CodingTask]` (receives Coder output automatically) |
| `agent` | `ReviewerAgent` |

---

### `LLMConfig`

Configuration value object resolved by `make_llm()` from environment variables.

| Field | Env Var | Default |
|---|---|---|
| `provider` | `LLM_PROVIDER` | `"ollama"` |
| `model` | `LLM_MODEL` | `"qwen2.5-coder:7b"` |
| `base_url` | `OLLAMA_BASE_URL` | `"http://localhost:11434"` |
| `temperature` | `LLM_TEMPERATURE` | `0.2` |

---

## Inputs / Outputs

### Entry Point Input

```
working_directory : str | Path   — directory to write output files
project_name      : str          — used as the output file base name
requirement       : str          — natural language coding requirement
```

### Entry Point Output

```
CrewOutput                        — CrewAI result object
  .raw          : str            — raw string of the final task output (review report)
  .tasks_output : list[TaskOutput] — per-task outputs including the generated code
```

Generated file on disk:
```
{working_directory}/{project_name}.py   — Python source produced by CoderAgent
```

---

## State Transitions

```
Created → Running → Completed
                 → Failed (LLM error, connectivity, invalid config)
```

No state is persisted. Each `CodingCrew.run()` call is stateless and idempotent from a data perspective (output file is overwritten on re-run).
