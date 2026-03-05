"""Smoke tests for simple_crewai_coding_agent — require a live Ollama instance.

These tests exercise the full end-to-end stack with a real LLM.
They are NOT run in CI. Run manually after configuring your .env:

    ollama pull qwen2.5-coder:7b
    cp .env.example .env
    uv run pytest tests/integration/test_smoke.py -m smoke -v

Prerequisites:
- Ollama running locally (default: http://localhost:11434)
- qwen2.5-coder:7b model pulled (or override LLM_MODEL in .env)
"""

import pytest
from dotenv import load_dotenv

# Load .env if present so smoke tests pick up user configuration
load_dotenv()


@pytest.mark.smoke
def test_run_crew_produces_valid_python_file(tmp_working_dir):
    """Full end-to-end: agent writes a Python file containing a valid function."""
    from simple_crewai_coding_agent import run_crew

    result = run_crew(
        working_directory=tmp_working_dir,
        project_name="adder",
        requirement=(
            "Write a Python function named 'add' that takes two numbers and returns their sum."
        ),
    )

    # File must exist on disk
    assert result.output_file.exists(), "Output file was not written to disk"

    # File must be non-empty
    assert result.output_file.stat().st_size > 0, "Output file is empty"

    # File must contain at least one function definition
    assert "def " in result.code, (
        f"Generated code does not contain a function definition. Got:\n{result.code[:500]}"
    )

    # Review report must be non-empty
    assert len(result.review.strip()) > 0, "Review report is empty"
