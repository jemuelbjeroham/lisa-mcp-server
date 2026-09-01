import json

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_search_knowledge_tool() -> None:
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

        result = await session.call_tool(
            "search_knowledge",
            {
                "query": "How do I troubleshoot firewall connectivity",
                "top_k": 5,
            },
        )

        assert not result.is_error
        assert len(result.content) == 1

        response = json.loads(result.content[0].text)

        assert "results" in response
        assert len(response["results"]) == 5