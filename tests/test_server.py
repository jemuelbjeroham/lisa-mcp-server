import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_health_check_tool() -> None:
    server_params = StdioServerParameters(
        command="uv",
        args=[
            "run",
            "python",
            "-m",
            "lisa_mcp_server.server",
        ],
    )

    async with (
          stdio_client(server_params) as (read, write),
          ClientSession(read, write) as session,
    ):
            await session.initialize()
            tools = await session.list_tools()

            assert any(
                tool.name == "health_check"
                for tool in tools.tools
            )

            result = await session.call_tool(
                "health_check",
                {},
            )

            assert result.content[0].text == (
                "LISA MCP Server is healthy"
            )