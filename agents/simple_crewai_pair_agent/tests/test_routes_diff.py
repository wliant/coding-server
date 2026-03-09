"""Tests for worker diff endpoints (GET /diff, GET /diff/{path})."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from worker.routes import make_router


def _make_app(work_dir_base: str = "/tmp/test-work") -> tuple[FastAPI, TestClient]:
    app = FastAPI()
    router = make_router(work_dir_base=work_dir_base, db_session_factory=None)
    app.include_router(router)
    return app, TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_worker_state():
    """Reset global _state before each test."""
    from worker import routes

    routes._state.status = "free"
    routes._state.task_id = None
    routes._state.error_message = None
    routes._state.git_url = None
    routes._state.github_token = None
    routes._state.work_dir_path = None
    yield


def _make_git_repo(path):
    """Initialise a git repo with one committed README.md."""
    import git as gitpython

    repo = gitpython.Repo.init(str(path))
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    readme = path / "README.md"
    readme.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    return repo


# ---------------------------------------------------------------------------
# GET /diff?task_id=  — list changed files
# ---------------------------------------------------------------------------


def test_diff_list_404_when_task_id_dir_missing(tmp_path):
    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/diff?task_id=missing-task")
    assert resp.status_code == 404


def test_diff_list_400_when_not_git_repo(tmp_path):
    work_dir = tmp_path / "not-git-task"
    work_dir.mkdir()
    (work_dir / "file.txt").write_text("hello")

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/diff?task_id=not-git-task")
    assert resp.status_code == 400


def test_diff_list_empty_for_clean_repo(tmp_path):
    work_dir = tmp_path / "clean-task"
    work_dir.mkdir()
    _make_git_repo(work_dir)

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/diff?task_id=clean-task")
    assert resp.status_code == 200
    data = resp.json()
    assert data["changed_files"] == []
    assert data["total_additions"] == 0
    assert data["total_deletions"] == 0


def test_diff_list_shows_modified_file(tmp_path):
    work_dir = tmp_path / "modified-task"
    work_dir.mkdir()
    _make_git_repo(work_dir)
    # Modify the committed file
    (work_dir / "README.md").write_text("# Updated\nnew line\n")

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/diff?task_id=modified-task")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["changed_files"]) == 1
    entry = data["changed_files"][0]
    assert entry["path"] == "README.md"
    assert entry["change_type"] == "modified"
    assert entry["deletions"] > 0


def test_diff_list_shows_untracked_file_as_added(tmp_path):
    work_dir = tmp_path / "added-task"
    work_dir.mkdir()
    _make_git_repo(work_dir)
    # New untracked file
    (work_dir / "new_file.py").write_text("x = 1\ny = 2\n")

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/diff?task_id=added-task")
    assert resp.status_code == 200
    data = resp.json()
    paths = [e["path"] for e in data["changed_files"]]
    assert "new_file.py" in paths
    added = next(e for e in data["changed_files"] if e["path"] == "new_file.py")
    assert added["change_type"] == "added"
    assert added["additions"] == 2


def test_diff_list_shows_deleted_file(tmp_path):
    work_dir = tmp_path / "deleted-task"
    work_dir.mkdir()
    repo = _make_git_repo(work_dir)
    # Add and commit a second file, then delete it from working tree
    extra = work_dir / "extra.txt"
    extra.write_text("bye\n")
    repo.index.add(["extra.txt"])
    repo.index.commit("Add extra.txt")
    extra.unlink()  # delete from disk (not staged)

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/diff?task_id=deleted-task")
    assert resp.status_code == 200
    data = resp.json()
    deleted_entries = [e for e in data["changed_files"] if e["change_type"] == "deleted"]
    assert any(e["path"] == "extra.txt" for e in deleted_entries)


def test_diff_list_falls_back_to_state(tmp_path):
    from worker import routes

    work_dir = tmp_path / "state-diff-task"
    work_dir.mkdir()
    _make_git_repo(work_dir)
    routes._state.work_dir_path = str(work_dir)

    _, client = _make_app()
    resp = client.get("/diff")
    assert resp.status_code == 200
    data = resp.json()
    assert "changed_files" in data


# ---------------------------------------------------------------------------
# GET /diff/{path}?task_id=  — single file diff
# ---------------------------------------------------------------------------


def test_file_diff_modified_file(tmp_path):
    work_dir = tmp_path / "file-diff-task"
    work_dir.mkdir()
    _make_git_repo(work_dir)
    (work_dir / "README.md").write_text("# Updated\nnew line\n")

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/diff/README.md?task_id=file-diff-task")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_new_file"] is False
    assert "-" in data["diff"] or "+" in data["diff"]


def test_file_diff_new_untracked_file(tmp_path):
    work_dir = tmp_path / "new-file-task"
    work_dir.mkdir()
    _make_git_repo(work_dir)
    (work_dir / "new_file.py").write_text("x = 1\n")

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/diff/new_file.py?task_id=new-file-task")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_new_file"] is True
    assert data["diff"].startswith("--- /dev/null")


def test_file_diff_403_path_traversal(tmp_path):
    work_dir = tmp_path / "sec-diff-task"
    work_dir.mkdir()
    _make_git_repo(work_dir)

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/diff/../../etc/passwd?task_id=sec-diff-task")
    # Either 403 (handler guard) or 404 (URL normalized by HTTP layer — traversal still blocked)
    assert resp.status_code in (403, 404)


def test_file_diff_404_nonexistent_file(tmp_path):
    work_dir = tmp_path / "miss-diff-task"
    work_dir.mkdir()
    _make_git_repo(work_dir)

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/diff/nonexistent.py?task_id=miss-diff-task")
    assert resp.status_code == 404


def test_file_diff_404_unchanged_file(tmp_path):
    work_dir = tmp_path / "unchanged-diff-task"
    work_dir.mkdir()
    _make_git_repo(work_dir)
    # README.md is committed and unchanged — no diff

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/diff/README.md?task_id=unchanged-diff-task")
    assert resp.status_code == 404
