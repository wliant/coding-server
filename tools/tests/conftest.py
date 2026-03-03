import pytest
from fastmcp import Client

from tools.servers.filesystem_server import mcp as filesystem_mcp


@pytest.fixture
async def filesystem_client():
    """In-process FastMCP client for filesystem server tests."""
    async with Client(filesystem_mcp) as client:
        yield client
