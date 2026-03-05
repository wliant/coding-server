"""CLI entry point for simple_crewai_coding_agent.

Usage:
    uv run python -m simple_crewai_coding_agent \\
        --working-dir ./output \\
        --project-name calculator \\
        --requirement "Write a Python module with add, subtract, multiply functions."
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present before any LLM configuration is read
load_dotenv()

from simple_crewai_coding_agent.logging_config import configure_logging  # noqa: E402

configure_logging()

# CrewAI validates OPENAI_API_KEY at import time; set a dummy for non-OpenAI providers
os.environ.setdefault("OPENAI_API_KEY", "NA")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="simple_crewai_coding_agent",
        description="Run a CrewAI coding agent to generate Python code from a requirement.",
    )
    parser.add_argument(
        "--working-dir",
        required=True,
        metavar="PATH",
        help="Directory where the generated code file will be written.",
    )
    parser.add_argument(
        "--project-name",
        required=True,
        metavar="NAME",
        help="Base name for the output file (e.g. 'calculator' → 'calculator.py').",
    )
    parser.add_argument(
        "--requirement",
        required=True,
        metavar="TEXT",
        help="Natural-language description of what code to produce.",
    )

    args = parser.parse_args()

    # Deferred import: keeps module-level side effects (logging, env setup) contained
    # to CLI invocation and avoids importing crewai until args are validated.
    from simple_crewai_coding_agent import run_crew

    try:
        result = run_crew(
            working_directory=Path(args.working_dir),
            project_name=args.project_name,
            requirement=args.requirement,
        )
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Output file: {result.output_file}")
    print("\n--- Review ---")
    print(result.review)


if __name__ == "__main__":
    main()
