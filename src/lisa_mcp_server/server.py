from mcp.server.mcpserver import MCPServer

from lisa_mcp_server.net_tools_client import NetToolsClient

mcp = MCPServer("LISA MCP SERVER")

net_tools_client = NetToolsClient(base_url="http://127.0.0.1:8000")

@mcp.tool()
def health_check() -> str:
    """
    Check whether the MCP server is running
    """
    return "LISA MCP Server is healthy"

@mcp.tool()
async def search_knowledge(query: str, top_k: int=5) -> dict:
    """
    Search the Network Operations Knowledge Base
    """
    return await net_tools_client.search(query=query, top_k=top_k)

if __name__ == "__main__":
    mcp.run()