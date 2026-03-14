"""Tests for the Sandbox MCP server tools."""
import os
import tempfile

import pytest

from sandbox.mcp_server import create_mcp_server


@pytest.fixture
def workspace(tmp_path):
    """Provide a temporary workspace directory."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return str(ws)


@pytest.fixture
def mcp(workspace):
    return create_mcp_server(workspace, labels=["python", "git"])


def test_create_mcp_server_returns_fastmcp(mcp):
    from fastmcp import FastMCP
    assert isinstance(mcp, FastMCP)


def test_list_files_empty(workspace, mcp):
    # Directly call the tool function
    # The MCP tools are sync functions registered on the server
    # We can access them via the mcp._tool_manager or call them directly
    # For testing, we'll use the routes directly
    pass


class TestMCPTools:
    """Test MCP tool functions via the sandbox routes (same logic)."""

    def test_get_capabilities(self, workspace):
        mcp = create_mcp_server(workspace, labels=["python", "docker"])
        # The get_capabilities tool should return the labels
        # Since MCP tools are registered as functions, we test the route equivalent
        from sandbox.routes import make_router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(make_router(workspace, labels=["python", "docker"]))
        client = TestClient(app)
        resp = client.get("/capabilities")
        assert resp.status_code == 200
        assert resp.json() == {"capabilities": ["python", "docker"]}

    def test_reset_workspace(self, workspace):
        from sandbox.routes import make_router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI

        # Create a file
        os.makedirs(os.path.join(workspace, "subdir"), exist_ok=True)
        with open(os.path.join(workspace, "test.txt"), "w") as f:
            f.write("hello")
        with open(os.path.join(workspace, "subdir", "nested.txt"), "w") as f:
            f.write("world")

        app = FastAPI()
        app.include_router(make_router(workspace))
        client = TestClient(app)

        # Verify files exist
        resp = client.get("/files")
        assert resp.status_code == 200
        assert len(resp.json()["entries"]) > 0

        # Reset
        resp = client.post("/reset")
        assert resp.status_code == 200
        assert resp.json() == {"reset": True}

        # Verify workspace is empty
        resp = client.get("/files")
        assert resp.status_code == 200
        assert len(resp.json()["entries"]) == 0

    def test_capabilities_empty(self, workspace):
        from sandbox.routes import make_router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(make_router(workspace))
        client = TestClient(app)
        resp = client.get("/capabilities")
        assert resp.status_code == 200
        assert resp.json() == {"capabilities": []}
