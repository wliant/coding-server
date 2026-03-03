from fastmcp import FastMCP
from tools.servers.filesystem_server import mcp as filesystem_mcp
from tools.servers.git_server import mcp as git_mcp
from tools.servers.shell_server import mcp as shell_mcp

mcp = FastMCP("tool-gateway")

mcp.mount(filesystem_mcp, namespace="filesystem")
mcp.mount(git_mcp, namespace="git")
mcp.mount(shell_mcp, namespace="shell")


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8002)
