# Quickstart: simple_crewai_coding_agent

**Feature**: 004-crewai-coding-agent
**Date**: 2026-03-04

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- [Ollama](https://ollama.com/download) installed and running locally
- The `qwen2.5-coder:7b` model pulled: `ollama pull qwen2.5-coder:7b`

---

## Setup

```bash
# From the repo root, navigate to the module
cd simple_crewai_coding_agent

# Install dependencies (creates .venv automatically)
uv sync

# Copy the env template and configure
cp .env.example .env
# Edit .env if you want to use a different LLM provider or model
```

### `.env` defaults (Ollama)

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:7b
OLLAMA_BASE_URL=http://localhost:11434
LLM_TEMPERATURE=0.2
OPENAI_API_KEY=NA
```

### Using a different LLM

To use OpenAI instead of Ollama, update `.env`:
```dotenv
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

To use Anthropic:
```dotenv
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Run the Agent

```python
from pathlib import Path
from simple_crewai_coding_agent import run_crew

result = run_crew(
    working_directory=Path("./output"),
    project_name="calculator",
    requirement="Write a Python module with add, subtract, multiply, and divide functions.",
)

print("Generated code saved to:", result.output_file)
print("Review:", result.review)
```

Or via the CLI entry point:

```bash
uv run python -m simple_crewai_coding_agent \
  --working-dir ./output \
  --project-name calculator \
  --requirement "Write a Python module with add, subtract, multiply, and divide functions."
```

---

## Run Tests

```bash
# Unit + integration tests (no Ollama required — LLM is mocked)
uv run pytest tests/ -m "not smoke"

# Smoke tests (requires running Ollama with qwen2.5-coder:7b)
uv run pytest tests/ -m smoke -v
```

---

## Lint

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```
