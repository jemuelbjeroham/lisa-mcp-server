import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from lisa_mcp_server.net_tools_client import NetToolsClient


def test_jira_client_preserves_read_routes_and_payloads():
    responses = {
        "success": True,
        "ticket_key": "OPS-123",
        "ticket_url": "https://jira.example/browse/OPS-123",
    }
    calls = []

    def handler(request):
        import json

        calls.append((request.method, request.url.path, json.loads(request.content)))
        return httpx.Response(200, json=responses)

    async def run():
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with patch(
            "lisa_mcp_server.net_tools_client.httpx.AsyncClient", return_value=transport
        ):
            client = NetToolsClient("http://backend/")
            assert client.base_url == "http://backend/"
            await client.search_jira_tickets("project = OPS", 10, "page2")

    asyncio.run(run())
    assert calls[0] == (
        "POST",
        "/api/v1/jira/search",
        {"jql": "project = OPS", "max_results": 10, "next_page_token": "page2"},
    )
    assert len(calls) == 1


def test_mcp_tools_are_registered_and_forward_arguments():
    from lisa_mcp_server import server

    async def run():
        tools = {tool.name: tool for tool in await server.mcp.list_tools()}
        assert {
            "create_jira_ticket",
            "update_jira_ticket",
            "search_jira_tickets",
            "close_ticket",
        } <= tools.keys()
        assert "assign_ticket" not in tools
        assert set(tools["create_jira_ticket"].input_schema["required"]) == {
            "subject",
            "description",
        }
        assert set(tools["create_jira_ticket"].input_schema["properties"]) == {
            "subject", "description", "project_key", "issue_type", "priority", "labels",
        }
        assert tools["update_jira_ticket"].input_schema["required"] == ["ticket_key", "comment"]
        assert set(tools["update_jira_ticket"].input_schema["properties"]) == {"ticket_key", "comment"}
        assert tools["search_jira_tickets"].input_schema["required"] == ["jql"]
        assert tools["close_ticket"].input_schema["required"] == ["ticket_id"]
        assert set(tools["close_ticket"].input_schema["properties"]) == {"ticket_id"}
        with patch.object(server, "net_tools_client") as client:
            client.create_jira_ticket = AsyncMock(
                return_value={"ticket_key": "OPS-123"}
            )
            client.update_jira_ticket = AsyncMock(return_value={"success": True})
            client.close_ticket = AsyncMock(return_value={"success": True, "ticket_key": "OPS-123"})
            client.search_jira_tickets = AsyncMock(return_value={"tickets": []})
            assert (await server.create_jira_ticket("Alarm", "Details", "OPS", "Task", "High", ["network"])).is_error
            assert (await server.update_jira_ticket("OPS-123", "Recovered")).is_error
            assert (await server.close_ticket("123")).is_error
            await server.search_jira_tickets("project = OPS", 10, "next")
            client.create_jira_ticket.assert_not_called()
            client.update_jira_ticket.assert_not_called()
            client.close_ticket.assert_not_called()
            client.search_jira_tickets.assert_awaited_once_with(
                "project = OPS", 10, "next"
            )

    asyncio.run(run())


def test_mcp_client_surfaces_backend_errors_without_retry():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            503, json={"detail": "Jira credentials are not configured"}
        )

    async def run():
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with (
            patch(
                "lisa_mcp_server.net_tools_client.httpx.AsyncClient",
                return_value=transport,
            ),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await NetToolsClient("http://backend").search_jira_tickets("project = OPS")

    asyncio.run(run())
    assert len(calls) == 1


@pytest.mark.parametrize("ambient_config", [False, True])
def test_client_writes_deny_before_network_even_with_ambient_config(monkeypatch, ambient_config):
    for name in ("NET_TOOLS_SERVICE_TOKEN", "LISA_HITL_SERVICE_TOKEN", "LISA_HITL_AUTHORITY_URL", "LISA_USER_ID", "LISA_EXECUTION_CAPABILITY"):
        if ambient_config:
            monkeypatch.setenv(name, "untrusted-ambient-test-value")
        else:
            monkeypatch.delenv(name, raising=False)

    async def run():
        client = NetToolsClient("http://backend")
        with patch("lisa_mcp_server.net_tools_client.httpx.AsyncClient") as outbound:
            results = [await client.create_jira_ticket("Alarm", "Details", "OPS", "Task"),
                await client.update_jira_ticket("OPS-123", "Recovered"), await client.close_ticket("OPS-123"),
                await client._jira_request("POST", "/api/v1/jira/tickets", {})]
            import json
            for result in results:
                assert result.is_error
                assert json.loads(result.content[0].text) == {"accepted": False, "error": "approval_required"}
            outbound.assert_not_called()

    asyncio.run(run())


def test_read_client_does_not_inject_ambient_auth(monkeypatch):
    monkeypatch.setenv("NET_TOOLS_SERVICE_TOKEN", "ambient-test-token")
    monkeypatch.setenv("LISA_EXECUTION_CAPABILITY", "ambient-test-capability")
    calls = []

    def handler(request):
        calls.append(request)
        assert "authorization" not in request.headers
        assert "x-lisa-execution" not in request.headers
        return httpx.Response(200, json={})

    async def run():
        client = NetToolsClient("http://backend")
        for method, arguments in (
            (client.search, ("query",)),
            (client.search_jira_tickets, ("project = OPS",)),
        ):
            transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            with patch("lisa_mcp_server.net_tools_client.httpx.AsyncClient", return_value=transport):
                await method(*arguments)

    asyncio.run(run())
    assert len(calls) == 2
