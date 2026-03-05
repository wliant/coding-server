"""Unit tests for the CLI entry point (__main__.py)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_missing_args_exits_nonzero() -> None:
    """Calling main() with no args should print usage and exit non-zero."""
    with patch.object(sys, "argv", ["simple-crewai-coding-agent"]):
        from simple_crewai_coding_agent.__main__ import main

        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0


def test_empty_requirement_exits_one(tmp_path: Path) -> None:
    """An empty requirement string causes run_crew to raise ValueError → exit 1."""
    args = [
        "simple-crewai-coding-agent",
        "--working-dir", str(tmp_path),
        "--project-name", "test",
        "--requirement", "",
    ]
    fake_result = MagicMock()
    fake_result.output_file = tmp_path / "test.py"
    fake_result.review = ""

    with (
        patch.object(sys, "argv", args),
        patch(
            "simple_crewai_coding_agent.run_crew",
            side_effect=ValueError("requirement must not be empty"),
        ),
    ):
        from simple_crewai_coding_agent.__main__ import main

        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


def test_happy_path_calls_run_crew(tmp_path: Path) -> None:
    """Valid args should call run_crew and exit 0 (no SystemExit)."""
    args = [
        "simple-crewai-coding-agent",
        "--working-dir", str(tmp_path),
        "--project-name", "hello",
        "--requirement", "write a hello function",
    ]
    fake_result = MagicMock()
    fake_result.output_file = tmp_path / "hello.py"
    fake_result.review = "Looks good."

    with (
        patch.object(sys, "argv", args),
        patch("simple_crewai_coding_agent.run_crew", return_value=fake_result) as mock_run,
    ):
        from simple_crewai_coding_agent.__main__ import main

        main()  # should not raise

    mock_run.assert_called_once_with(
        working_directory=tmp_path,
        project_name="hello",
        requirement="write a hello function",
    )
