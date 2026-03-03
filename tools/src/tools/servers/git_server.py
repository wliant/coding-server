from fastmcp import FastMCP

mcp = FastMCP("git")


@mcp.tool()
async def git_clone(url: str, destination: str) -> str:
    """Clone a git repository."""
    raise NotImplementedError("git:git_clone not yet implemented")


@mcp.tool()
async def git_status(repo_path: str) -> str:
    """Get git status of a repository."""
    raise NotImplementedError("git:git_status not yet implemented")
