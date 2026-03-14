"""Service for proxying file browsing requests to workers, sandboxes, or temp clones."""

import asyncio
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.services.task_service import get_task_detail

# Temp clone cache: task_id -> (path, created_at)
_temp_clones: dict[str, tuple[str, float]] = {}
_clone_lock = asyncio.Lock()

TEMP_CLONE_DIR = os.environ.get("TEMP_CLONE_DIR", tempfile.gettempdir() + "/task-browse")
TEMP_CLONE_TTL_SECONDS = int(os.environ.get("TEMP_CLONE_TTL_SECONDS", "1800"))


async def _get_file_source(
    db: AsyncSession, task_id: uuid.UUID
) -> tuple[str, str]:
    """Determine the file source URL and type for a task.

    Returns (base_url, source_type) where source_type is one of:
    - "worker": proxy to assigned worker
    - "git": clone from git_url
    - "unavailable": no source available

    Raises HTTPException 404 if task not found.
    """
    detail = await get_task_detail(db, task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Task not found")

    job, project, _work_dir, _agent = detail

    # If sandbox is assigned, proxy to it
    if getattr(job, "assigned_sandbox_url", None):
        return job.assigned_sandbox_url, "worker"  # sandbox uses same /files API

    # If worker is assigned, proxy to it
    if job.assigned_worker_url:
        return job.assigned_worker_url, "worker"

    # If pending/in_progress with git_url, use temp clone
    if project.git_url and job.status in ("pending", "in_progress"):
        return project.git_url, "git"

    raise HTTPException(
        status_code=404,
        detail="No file source available for this task",
    )


async def _ensure_temp_clone(git_url: str, task_id: str) -> str:
    """Ensure a shallow clone exists for the given task. Returns the clone path."""
    async with _clone_lock:
        if task_id in _temp_clones:
            path, created_at = _temp_clones[task_id]
            if os.path.isdir(path) and (time.time() - created_at) < TEMP_CLONE_TTL_SECONDS:
                return path
            # Expired or missing — remove and re-clone
            shutil.rmtree(path, ignore_errors=True)
            del _temp_clones[task_id]

        clone_dir = os.path.join(TEMP_CLONE_DIR, task_id)
        os.makedirs(clone_dir, exist_ok=True)

        # Run shallow clone in a thread to avoid blocking
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth", "1", git_url, clone_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            shutil.rmtree(clone_dir, ignore_errors=True)
            raise HTTPException(
                status_code=502,
                detail=f"Failed to clone repository: {stderr.decode()[:500]}",
            )

        _temp_clones[task_id] = (clone_dir, time.time())
        return clone_dir


def _list_files_from_dir(base_path: str) -> list[dict]:
    """List files recursively from a directory, excluding .git."""
    entries = []
    base = Path(base_path)
    for item in sorted(base.rglob("*")):
        rel = item.relative_to(base)
        # Skip .git directory
        if ".git" in rel.parts:
            continue
        entry = {
            "name": item.name,
            "path": str(rel).replace("\\", "/"),
            "type": "directory" if item.is_dir() else "file",
        }
        if item.is_file():
            entry["size"] = item.stat().st_size
            # Check if binary
            try:
                with open(item, "rb") as f:
                    chunk = f.read(8192)
                    entry["is_binary"] = b"\x00" in chunk
            except OSError:
                entry["is_binary"] = True
        entries.append(entry)
    return entries


def _read_file_from_dir(base_path: str, file_path: str) -> dict:
    """Read a single file from a directory."""
    full_path = Path(base_path) / file_path
    # Security: ensure path doesn't escape base
    try:
        full_path.resolve().relative_to(Path(base_path).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Path traversal not allowed")

    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    size = full_path.stat().st_size
    max_size = 500 * 1024  # 500 KB

    try:
        with open(full_path, "rb") as f:
            chunk = f.read(8192)
            is_binary = b"\x00" in chunk

        if is_binary:
            return {
                "path": file_path,
                "content": "",
                "size": size,
                "is_binary": True,
            }

        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_size)
            if size > max_size:
                content += f"\n\n[Truncated — file is {size:,} bytes, showing first {max_size:,}]"

        return {
            "path": file_path,
            "content": content,
            "size": size,
            "is_binary": False,
        }
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


async def list_task_files(db: AsyncSession, task_id: uuid.UUID) -> dict:
    """List files for a task, proxying to the appropriate source."""
    base_url, source_type = await _get_file_source(db, task_id)

    if source_type == "worker":
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{base_url}/files",
                params={"task_id": str(task_id)},
            )
            resp.raise_for_status()
            return resp.json()

    if source_type == "git":
        clone_path = await _ensure_temp_clone(base_url, str(task_id))
        entries = _list_files_from_dir(clone_path)
        return {"root": clone_path, "entries": entries}

    raise HTTPException(status_code=404, detail="No file source available")


async def get_task_file_content(
    db: AsyncSession, task_id: uuid.UUID, file_path: str
) -> dict:
    """Get file content for a task, proxying to the appropriate source."""
    base_url, source_type = await _get_file_source(db, task_id)

    if source_type == "worker":
        encoded = "/".join(part for part in file_path.split("/"))
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{base_url}/files/{encoded}",
                params={"task_id": str(task_id)},
            )
            resp.raise_for_status()
            return resp.json()

    if source_type == "git":
        clone_path = await _ensure_temp_clone(base_url, str(task_id))
        return _read_file_from_dir(clone_path, file_path)

    raise HTTPException(status_code=404, detail="No file source available")


def cleanup_temp_clone(task_id: str) -> None:
    """Remove a temp clone for a task (e.g., when task transitions out of pending)."""
    if task_id in _temp_clones:
        path, _ = _temp_clones.pop(task_id)
        shutil.rmtree(path, ignore_errors=True)


def cleanup_expired_clones() -> None:
    """Remove all expired temp clones."""
    now = time.time()
    expired = [
        tid for tid, (_, created_at) in _temp_clones.items()
        if now - created_at > TEMP_CLONE_TTL_SECONDS
    ]
    for tid in expired:
        path, _ = _temp_clones.pop(tid)
        shutil.rmtree(path, ignore_errors=True)
