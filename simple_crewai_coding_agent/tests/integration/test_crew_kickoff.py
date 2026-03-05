"""Integration tests for crew.kickoff() with mocked LLM — no real Ollama required."""

import pytest


def test_run_crew_creates_output_file(tmp_working_dir, mock_llm_call):
    from simple_crewai_coding_agent import run_crew

    result = run_crew(
        working_directory=tmp_working_dir,
        project_name="calculator",
        requirement="write an add function",
    )
    assert result.output_file.exists(), "Output file should be written to disk"
    assert result.output_file.stat().st_size > 0, "Output file should be non-empty"


def test_run_crew_returns_non_empty_code(tmp_working_dir, mock_llm_call):
    from simple_crewai_coding_agent import run_crew

    result = run_crew(
        working_directory=tmp_working_dir,
        project_name="calculator",
        requirement="write an add function",
    )
    assert isinstance(result.code, str)
    assert len(result.code.strip()) > 0, "result.code should be non-empty"


def test_run_crew_returns_review(tmp_working_dir, mock_llm_call):
    from simple_crewai_coding_agent import run_crew

    result = run_crew(
        working_directory=tmp_working_dir,
        project_name="calculator",
        requirement="write an add function",
    )
    assert isinstance(result.review, str)
    assert len(result.review.strip()) > 0, "result.review should be non-empty"


def test_run_crew_output_file_path_matches_project_name(tmp_working_dir, mock_llm_call):
    from simple_crewai_coding_agent import run_crew

    result = run_crew(
        working_directory=tmp_working_dir,
        project_name="my_module",
        requirement="write a hello function",
    )
    assert result.output_file.name == "my_module.py"
    assert result.output_file.parent == tmp_working_dir


def test_run_crew_creates_working_directory_if_missing(tmp_path, mock_llm_call):
    from simple_crewai_coding_agent import run_crew

    new_dir = tmp_path / "new_subdir" / "nested"
    assert not new_dir.exists()
    result = run_crew(
        working_directory=new_dir,
        project_name="calc",
        requirement="write an add function",
    )
    assert new_dir.exists()
    assert result.output_file.exists()


def test_run_crew_raises_on_empty_requirement(tmp_working_dir):
    from simple_crewai_coding_agent import run_crew

    with pytest.raises(ValueError, match="requirement"):
        run_crew(
            working_directory=tmp_working_dir,
            project_name="calc",
            requirement="   ",
        )


def test_run_crew_raises_on_empty_project_name(tmp_working_dir):
    from simple_crewai_coding_agent import run_crew

    with pytest.raises(ValueError, match="project_name"):
        run_crew(
            working_directory=tmp_working_dir,
            project_name="",
            requirement="write an add function",
        )
