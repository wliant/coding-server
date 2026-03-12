from pathlib import Path

import pytest


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Provide a temporary workspace directory for sandbox tests."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws
