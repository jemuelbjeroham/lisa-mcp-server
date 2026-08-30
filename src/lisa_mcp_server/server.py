from mcp.server.mcpserver import MCPServer

mcp = MCPServer("LISA MCP SERVER")

@mcp.tool()
def health_check() -> str:
    """
    Check whether the MCP server is running
    """
    return "LISA MCP Server is healthy"

if __name__ == "__main__":
    mcp.run()