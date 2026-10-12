import os

from mcp.server.mcpserver import MCPServer

from lisa_mcp_server.internet_client import InternetClient
from lisa_mcp_server.net_tools_client import NetToolsClient

mcp = MCPServer("LISA MCP SERVER")

net_tools_client = NetToolsClient(base_url=os.getenv("NET_TOOLS_API_URL", "http://127.0.0.1:8000"))
internet_client = InternetClient(base_url=os.getenv("AGENT_SEARCH_API_URL", "http://127.0.0.1:3939"))

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

@mcp.tool()
async def web_search(query: str, count: int=5) -> dict:
    """
    Search the web and return ranked results without fetching page content.
    """
    return await internet_client.search(
        query=query,
        count=count,
        fetch=False,
    )

@mcp.tool()
async def web_search_with_content(query: str, count: int=5) -> dict:
    """
    Search the web and fetch page content for the returned results.
    """
    return await internet_client.search(
        query=query,
        count=count,
        fetch=True,
    )


if __name__ == "__main__":
    mcp.run()