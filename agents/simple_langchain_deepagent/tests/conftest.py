from pathlib import Path

import pytest


@pytest.fixture()
def tmp_working_dir(tmp_path: Path) -> Path:
    """Return a temporary directory path for use as the agent working directory."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    return work_dir
