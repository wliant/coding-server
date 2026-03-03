from fastmcp import FastMCP

mcp = FastMCP("shell")


@mcp.tool()
async def run_command(command: str, cwd: str) -> str:
    """Run a shell command in a directory."""
    raise NotImplementedError("shell:run_command not yet implemented")
