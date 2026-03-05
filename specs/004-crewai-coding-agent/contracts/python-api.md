# Contract: Python Public API

**Module**: `simple_crewai_coding_agent`
**Contract Type**: Python library interface
**Version**: 1.0.0
**Date**: 2026-03-04

---

## Rationale

This module has no REST API. Its contract is the Python function signature and return type exposed by the `simple_crewai_coding_agent` package. Consumers (tests, future worker integrations) depend only on this contract, not on internal implementation details.

---

## Public Entry Point

### `run_crew`

```python
def run_crew(
    working_directory: str | Path,
    project_name: str,
    requirement: str,
) -> CrewRunResult:
    """
    Execute the CrewAI coding crew for a given requirement.

    Args:
        working_directory: Path to the directory where generated code will be written.
                           The directory is created if it does not exist.
        project_name:      Human-readable name for the project. Used as the base
                           filename for the generated source file
                           (e.g., "my_project" → "my_project.py").
        requirement:       Natural-language description of what code to produce.
                           Must be non-empty after stripping whitespace.

    Returns:
        CrewRunResult with generated code content and review report.

    Raises:
        ValueError:        If requirement is empty or project_name is empty.
        RuntimeError:      If the LLM is unreachable or returns an unrecoverable error.
        OSError:           If working_directory cannot be created or written to.
    """
```

---

### `CrewRunResult`

```python
@dataclass
class CrewRunResult:
    code: str           # Generated Python source code (content of output file)
    review: str         # Code review report from ReviewerAgent
    output_file: Path   # Absolute path to the written file
```

---

## LLM Configuration (Environment Variables)

Consumers configure the LLM by setting environment variables before calling `run_crew`. No source code modification is required.

| Variable | Type | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | string | `ollama` | Provider: `ollama`, `openai`, `anthropic` |
| `LLM_MODEL` | string | `qwen2.5-coder:7b` | Model name (without provider prefix) |
| `OLLAMA_BASE_URL` | string | `http://localhost:11434` | Ollama server base URL |
| `LLM_TEMPERATURE` | float string | `0.2` | Sampling temperature |
| `OPENAI_API_KEY` | string | `NA` | Required dummy value when not using OpenAI |

---

## Stability Guarantees

- `run_crew()` signature is **stable** — callers MUST NOT depend on keyword-only argument ordering beyond what is shown above.
- `CrewRunResult` fields are **stable** — new fields may be added in minor versions; existing fields will not be removed in a 1.x release.
- Internal classes (`CodingCrew`, `CoderAgent`, `ReviewerAgent`, `make_llm`) are **internal** — not part of the public contract; may change without notice.

---

## Usage Example

```python
import os
from pathlib import Path
from simple_crewai_coding_agent import run_crew

# Configure LLM via env vars (or set them in .env)
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["LLM_MODEL"] = "qwen2.5-coder:7b"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OPENAI_API_KEY"] = "NA"

result = run_crew(
    working_directory=Path("/tmp/my_project"),
    project_name="calculator",
    requirement="Write a Python module with add, subtract, multiply, and divide functions.",
)

print(result.code)          # generated source
print(result.review)        # reviewer feedback
print(result.output_file)   # /tmp/my_project/calculator.py
```
