"""Sandbox workspace API routes."""
import io
import logging
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from sandbox.executor import execute_command, stream_command

logger = logging.getLogger(__name__)

_MAX_FILE_BYTES = 500 * 1024  # 500 KB


class ExecuteRequest(BaseModel):
    command: str
    timeout: int = 300


class ExecuteResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str


class WriteFileRequest(BaseModel):
    content: str


class FileEntry(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    size: int | None = None


class FileListResponse(BaseModel):
    root: str
    entries: list[FileEntry]


class FileContentResponse(BaseModel):
    path: str
    content: str
    size: int


def _is_binary(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
        return b"\x00" in chunk
    except OSError:
        return False


def make_router(workspace_dir: str, labels: list[str] | None = None) -> APIRouter:
    r = APIRouter()
    ws_root = Path(workspace_dir)
    _labels = labels or []

    def _resolve_path(path: str) -> Path:
        """Resolve and validate path is within workspace."""
        full = (ws_root / path).resolve()
        try:
            full.relative_to(ws_root.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=403, detail="Access outside workspace denied") from exc
        return full

    @r.get("/health")
    async def health():
        return {"status": "ok"}

    @r.get("/files", response_model=FileListResponse)
    async def list_files(path: str = ""):
        target = _resolve_path(path) if path else ws_root
        if not target.exists():
            raise HTTPException(status_code=404, detail="Directory not found")
        if not target.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        entries: list[FileEntry] = []
        for p in sorted(target.rglob("*")):
            rel = p.relative_to(ws_root)
            rel_str = str(rel).replace("\\", "/")
            # Skip .git directory
            if rel.parts[0] == ".git":
                continue
            if p.is_dir():
                entries.append(FileEntry(name=p.name, path=rel_str, type="directory"))
            else:
                entries.append(
                    FileEntry(name=p.name, path=rel_str, type="file", size=p.stat().st_size)
                )
        return FileListResponse(root=ws_root.name, entries=entries)

    @r.get("/files/{path:path}", response_model=FileContentResponse)
    async def get_file_content(path: str):
        full = _resolve_path(path)
        if not full.exists():
            raise HTTPException(status_code=404, detail="File not found")
        if full.is_dir():
            raise HTTPException(status_code=400, detail="Path is a directory")

        size = full.stat().st_size
        if _is_binary(full):
            raise HTTPException(status_code=400, detail="Binary file — use /download instead")

        with open(full, encoding="utf-8", errors="replace") as f:
            content = f.read(_MAX_FILE_BYTES)
        if size > _MAX_FILE_BYTES:
            content = "[TRUNCATED — file exceeds 500 KB]\n\n" + content
        return FileContentResponse(path=path, content=content, size=size)

    @r.put("/files/{path:path}")
    async def write_file(path: str, req: WriteFileRequest):
        full = _resolve_path(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(req.content, encoding="utf-8")
        return {"path": path, "size": len(req.content.encode("utf-8"))}

    @r.delete("/files/{path:path}")
    async def delete_file(path: str):
        full = _resolve_path(path)
        if not full.exists():
            raise HTTPException(status_code=404, detail="File not found")
        if full.is_dir():
            import shutil
            shutil.rmtree(full)
        else:
            full.unlink()
        return {"deleted": path}

    @r.post("/mkdir/{path:path}")
    async def create_directory(path: str):
        full = _resolve_path(path)
        full.mkdir(parents=True, exist_ok=True)
        return {"created": path}

    @r.get("/download")
    async def download_workspace():
        if not ws_root.exists():
            raise HTTPException(status_code=404, detail="Workspace not found")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in ws_root.rglob("*"):
                if file_path.is_file():
                    rel = file_path.relative_to(ws_root)
                    if rel.parts[0] == ".git":
                        continue
                    zf.write(file_path, rel)
        buf.seek(0)

        return Response(
            content=buf.read(),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=workspace.zip"},
        )

    @r.post("/execute", response_model=ExecuteResponse)
    async def execute(req: ExecuteRequest):
        result = await execute_command(req.command, cwd=workspace_dir, timeout=req.timeout)
        return ExecuteResponse(
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    @r.post("/execute/stream")
    async def execute_stream(req: ExecuteRequest):
        async def event_generator():
            async for event in stream_command(
                req.command, cwd=workspace_dir, timeout=req.timeout
            ):
                yield event

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    @r.get("/capabilities")
    async def get_capabilities():
        return {"capabilities": _labels}

    @r.post("/reset")
    async def reset_workspace():
        """Clear workspace directory contents (preserving the directory itself)."""
        import shutil

        if ws_root.exists():
            for item in ws_root.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        return {"reset": True}

    return r
