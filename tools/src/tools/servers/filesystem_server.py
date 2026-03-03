from fastmcp import FastMCP

mcp = FastMCP("filesystem")


@mcp.tool()
async def read_file(path: str) -> str:
    """Read contents of a file."""
    raise NotImplementedError("filesystem:read_file not yet implemented")


@mcp.tool()
async def write_file(path: str, content: str) -> None:
    """Write content to a file."""
    raise NotImplementedError("filesystem:write_file not yet implemented")
