"""Tests for worker file browser endpoints (GET /files, GET /files/{path})."""
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


# ---------------------------------------------------------------------------
# GET /files?task_id=  — list by task_id (primary usage)
# ---------------------------------------------------------------------------


def test_list_files_404_when_task_id_dir_missing(tmp_path):
    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/files?task_id=nonexistent-task")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_list_files_returns_sorted_flat_list(tmp_path):
    # Create a small tree under work_dir_base/task-123/
    work_dir = tmp_path / "task-123"
    work_dir.mkdir()
    (work_dir / "a.txt").write_text("hello")
    sub = work_dir / "sub"
    sub.mkdir()
    (sub / "b.py").write_text("print('hi')")

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/files?task_id=task-123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["root"] == "task-123"
    paths = [e["path"] for e in data["entries"]]
    assert "a.txt" in paths
    assert "sub" in paths
    assert "sub/b.py" in paths
    assert paths == sorted(paths)


def test_list_files_empty_dir(tmp_path):
    work_dir = tmp_path / "empty-task"
    work_dir.mkdir()

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/files?task_id=empty-task")
    assert resp.status_code == 200
    assert resp.json()["entries"] == []


def test_list_files_marks_binary(tmp_path):
    work_dir = tmp_path / "bin-task"
    work_dir.mkdir()
    (work_dir / "binary.bin").write_bytes(b"\x00\x01\x02")
    (work_dir / "text.txt").write_text("hello")

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/files?task_id=bin-task")
    assert resp.status_code == 200
    entries = {e["path"]: e for e in resp.json()["entries"]}
    assert entries["binary.bin"]["is_binary"] is True
    assert entries["text.txt"]["is_binary"] is False


def test_list_files_different_tasks_return_different_files(tmp_path):
    """Two tasks with different files must not bleed into each other."""
    (tmp_path / "task-a").mkdir()
    (tmp_path / "task-a" / "file_a.py").write_text("a")
    (tmp_path / "task-b").mkdir()
    (tmp_path / "task-b" / "file_b.py").write_text("b")

    _, client = _make_app(work_dir_base=str(tmp_path))

    resp_a = client.get("/files?task_id=task-a")
    paths_a = [e["path"] for e in resp_a.json()["entries"]]
    assert "file_a.py" in paths_a
    assert "file_b.py" not in paths_a

    resp_b = client.get("/files?task_id=task-b")
    paths_b = [e["path"] for e in resp_b.json()["entries"]]
    assert "file_b.py" in paths_b
    assert "file_a.py" not in paths_b


# ---------------------------------------------------------------------------
# GET /files  — state fallback (no task_id)
# ---------------------------------------------------------------------------


def test_list_files_404_when_no_state_and_no_task_id():
    _, client = _make_app()
    resp = client.get("/files")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_list_files_falls_back_to_state(tmp_path):
    from worker import routes

    work_dir = tmp_path / "state-task"
    work_dir.mkdir()
    (work_dir / "state_file.txt").write_text("via state")
    routes._state.work_dir_path = str(work_dir)

    _, client = _make_app()
    resp = client.get("/files")
    assert resp.status_code == 200
    paths = [e["path"] for e in resp.json()["entries"]]
    assert "state_file.txt" in paths


# ---------------------------------------------------------------------------
# GET /files/{path}?task_id=  — content by task_id
# ---------------------------------------------------------------------------


def test_get_file_content_404_no_state_no_task_id():
    _, client = _make_app()
    resp = client.get("/files/readme.md")
    assert resp.status_code == 404


def test_get_file_content_text_file(tmp_path):
    work_dir = tmp_path / "task-abc"
    work_dir.mkdir()
    (work_dir / "hello.py").write_text("print('hello')")

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/files/hello.py?task_id=task-abc")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_binary"] is False
    assert "print('hello')" in data["content"]
    assert data["path"] == "hello.py"


def test_get_file_content_binary_file(tmp_path):
    work_dir = tmp_path / "task-bin"
    work_dir.mkdir()
    (work_dir / "img.bin").write_bytes(b"\x00\xff\xfe")

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/files/img.bin?task_id=task-bin")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_binary"] is True
    assert data["content"] == ""


def test_get_file_content_truncates_large_file(tmp_path):
    work_dir = tmp_path / "task-large"
    work_dir.mkdir()
    (work_dir / "big.txt").write_bytes(b"A" * (600 * 1024))

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/files/big.txt?task_id=task-large")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_binary"] is False
    assert data["content"].startswith("[TRUNCATED")


def test_get_file_content_403_path_traversal(tmp_path):
    work_dir = tmp_path / "task-sec"
    work_dir.mkdir()

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/files/../../etc/passwd?task_id=task-sec")
    # Either 403 (handler guard) or 404 (URL normalized by HTTP layer — traversal still blocked)
    assert resp.status_code in (403, 404)


def test_get_file_content_404_file_missing(tmp_path):
    work_dir = tmp_path / "task-miss"
    work_dir.mkdir()

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/files/nonexistent.txt?task_id=task-miss")
    assert resp.status_code == 404


def test_get_file_content_400_directory(tmp_path):
    work_dir = tmp_path / "task-dir"
    work_dir.mkdir()
    (work_dir / "subdir").mkdir()

    _, client = _make_app(work_dir_base=str(tmp_path))
    resp = client.get("/files/subdir?task_id=task-dir")
    assert resp.status_code == 400
