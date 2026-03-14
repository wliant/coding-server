"""MCP server wrapping sandbox workspace operations as tools."""

import logging
from pathlib import Path

from fastmcp import FastMCP

from sandbox.executor import execute_command

logger = logging.getLogger(__name__)


def create_mcp_server(workspace_dir: str, labels: list[str] | None = None) -> FastMCP:
    """Create a FastMCP server exposing workspace operations as tools."""
    mcp = FastMCP("Sandbox Workspace")
    ws_root = Path(workspace_dir)
    _labels = labels or []

    def _resolve_path(path: str) -> Path:
        full = (ws_root / path).resolve()
        try:
            full.relative_to(ws_root.resolve())
        except ValueError:
            raise ValueError("Access outside workspace denied")
        return full

    @mcp.tool()
    def list_files(path: str = "") -> dict:
        """List files and directories in the workspace."""
        target = _resolve_path(path) if path else ws_root
        if not target.exists():
            return {"error": "Directory not found"}
        if not target.is_dir():
            return {"error": "Path is not a directory"}

        entries = []
        for p in sorted(target.rglob("*")):
            rel = p.relative_to(ws_root)
            rel_str = str(rel).replace("\\", "/")
            if rel.parts[0] == ".git":
                continue
            entry = {"name": p.name, "path": rel_str, "type": "directory" if p.is_dir() else "file"}
            if p.is_file():
                entry["size"] = p.stat().st_size
            entries.append(entry)
        return {"root": ws_root.name, "entries": entries}

    @mcp.tool()
    def read_file(path: str) -> dict:
        """Read the content of a file in the workspace."""
        full = _resolve_path(path)
        if not full.exists():
            return {"error": "File not found"}
        if full.is_dir():
            return {"error": "Path is a directory"}

        size = full.stat().st_size
        max_size = 500 * 1024

        try:
            with open(full, "rb") as f:
                chunk = f.read(8192)
                is_binary = b"\x00" in chunk

            if is_binary:
                return {"path": path, "content": "", "size": size, "is_binary": True}

            with open(full, encoding="utf-8", errors="replace") as f:
                content = f.read(max_size)

            return {"path": path, "content": content, "size": size, "is_binary": False}
        except OSError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def write_file(path: str, content: str) -> dict:
        """Write or overwrite a file in the workspace."""
        full = _resolve_path(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        return {"path": path, "size": len(content.encode("utf-8"))}

    @mcp.tool()
    def delete_file(path: str) -> dict:
        """Delete a file or directory in the workspace."""
        import shutil

        full = _resolve_path(path)
        if not full.exists():
            return {"error": "File not found"}
        if full.is_dir():
            shutil.rmtree(full)
        else:
            full.unlink()
        return {"deleted": path}

    @mcp.tool()
    def create_directory(path: str) -> dict:
        """Create a directory (and parent directories) in the workspace."""
        full = _resolve_path(path)
        full.mkdir(parents=True, exist_ok=True)
        return {"created": path}

    @mcp.tool()
    async def run_command(command: str, timeout: int = 300) -> dict:
        """Run a shell command in the workspace and return its output."""
        result = await execute_command(command, cwd=workspace_dir, timeout=timeout)
        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    @mcp.tool()
    def get_capabilities() -> dict:
        """Return the capabilities/labels available in this sandbox."""
        return {"capabilities": _labels}

    return mcp
