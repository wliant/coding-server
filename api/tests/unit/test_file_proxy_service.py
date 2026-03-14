"""Unit tests for the file proxy service.

NOTE: Tests that import api.services.file_proxy_service require gitpython,
so they run in Docker. Pure filesystem tests can run locally.
"""

import os
import tempfile
import time

import pytest
from fastapi import HTTPException

from api.models.job import Job


def test_list_files_from_dir():
    """_list_files_from_dir should list files and dirs, excluding .git."""
    from api.services.file_proxy_service import _list_files_from_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"))
        os.makedirs(os.path.join(tmpdir, ".git"))
        with open(os.path.join(tmpdir, "README.md"), "w") as f:
            f.write("# Hello")
        with open(os.path.join(tmpdir, "src", "main.py"), "w") as f:
            f.write("print('hello')")
        with open(os.path.join(tmpdir, ".git", "config"), "w") as f:
            f.write("git config")

        entries = _list_files_from_dir(tmpdir)
        paths = {e["path"] for e in entries}

        assert "README.md" in paths
        assert "src" in paths
        assert "src/main.py" in paths
        assert ".git" not in paths
        assert ".git/config" not in paths


def test_read_file_from_dir():
    """_read_file_from_dir should read file content correctly."""
    from api.services.file_proxy_service import _read_file_from_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "test.txt"), "w") as f:
            f.write("hello world")

        result = _read_file_from_dir(tmpdir, "test.txt")
        assert result["content"] == "hello world"
        assert result["is_binary"] is False
        assert result["path"] == "test.txt"


def test_read_file_path_traversal_blocked():
    """_read_file_from_dir should block path traversal."""
    from api.services.file_proxy_service import _read_file_from_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "test.txt"), "w") as f:
            f.write("safe")

        with pytest.raises(HTTPException) as exc_info:
            _read_file_from_dir(tmpdir, "../../../etc/passwd")
        assert exc_info.value.status_code == 403


def test_read_file_not_found():
    """_read_file_from_dir should raise 404 for missing files."""
    from api.services.file_proxy_service import _read_file_from_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(HTTPException) as exc_info:
            _read_file_from_dir(tmpdir, "nonexistent.txt")
        assert exc_info.value.status_code == 404


def test_list_files_detects_binary():
    """_list_files_from_dir should detect binary files."""
    from api.services.file_proxy_service import _list_files_from_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "binary.bin"), "wb") as f:
            f.write(b"\x00\x01\x02\x03")

        entries = _list_files_from_dir(tmpdir)
        binary_entry = next(e for e in entries if e["name"] == "binary.bin")
        assert binary_entry["is_binary"] is True


def test_read_file_binary_returns_empty_content():
    """_read_file_from_dir should return empty content for binary files."""
    from api.services.file_proxy_service import _read_file_from_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "binary.bin"), "wb") as f:
            f.write(b"\x00\x01\x02\x03")

        result = _read_file_from_dir(tmpdir, "binary.bin")
        assert result["is_binary"] is True
        assert result["content"] == ""


def test_cleanup_temp_clone():
    """cleanup_temp_clone should remove the clone from cache."""
    from api.services.file_proxy_service import _temp_clones, cleanup_temp_clone

    with tempfile.TemporaryDirectory() as tmpdir:
        _temp_clones["test-task"] = (tmpdir, 0)
        cleanup_temp_clone("test-task")
        assert "test-task" not in _temp_clones


def test_cleanup_expired_clones():
    """cleanup_expired_clones should remove old entries."""
    from api.services.file_proxy_service import (
        _temp_clones,
        cleanup_expired_clones,
        TEMP_CLONE_TTL_SECONDS,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        expired_time = time.time() - TEMP_CLONE_TTL_SECONDS - 100
        _temp_clones["expired-task"] = (tmpdir, expired_time)
        cleanup_expired_clones()
        assert "expired-task" not in _temp_clones


# --- DB-dependent tests (run in Docker) ---


async def test_get_file_source_returns_worker_when_assigned(db_session):
    """When a worker is assigned, file source should be the worker."""
    from api.services.file_proxy_service import _get_file_source
    from api.models.project import Project

    project = Project(name="Test", source_type="existing", status="active", git_url="https://github.com/org/repo.git")
    db_session.add(project)
    await db_session.flush()
    job = Job(
        project_id=project.id, requirement="test", status="completed",
        assigned_worker_url="http://worker:8001",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    url, source_type = await _get_file_source(db_session, job.id)
    assert source_type == "worker"
    assert url == "http://worker:8001"


async def test_get_file_source_returns_git_for_pending_task(db_session):
    """For a pending task with git_url, file source should be 'git'."""
    from api.services.file_proxy_service import _get_file_source
    from api.models.project import Project

    project = Project(name="Test", source_type="existing", status="active", git_url="https://github.com/org/repo.git")
    db_session.add(project)
    await db_session.flush()
    job = Job(project_id=project.id, requirement="test", status="pending")
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    url, source_type = await _get_file_source(db_session, job.id)
    assert source_type == "git"
    assert url == "https://github.com/org/repo.git"


async def test_get_file_source_raises_404_for_unknown_task(db_session):
    """Unknown task_id should raise 404."""
    import uuid
    from api.services.file_proxy_service import _get_file_source

    with pytest.raises(HTTPException) as exc_info:
        await _get_file_source(db_session, uuid.uuid4())
    assert exc_info.value.status_code == 404


async def test_get_file_source_raises_404_when_no_source(db_session):
    """Completed task without worker URL and no git_url should raise 404."""
    from api.services.file_proxy_service import _get_file_source
    from api.models.project import Project

    project = Project(name="Test", source_type="new", status="active")
    db_session.add(project)
    await db_session.flush()
    job = Job(project_id=project.id, requirement="test", status="completed")
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    with pytest.raises(HTTPException) as exc_info:
        await _get_file_source(db_session, job.id)
    assert exc_info.value.status_code == 404
