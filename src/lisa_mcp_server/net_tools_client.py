import json

import httpx
from mcp.types import CallToolResult, TextContent


def deny_jira_write() -> CallToolResult:
    return CallToolResult(is_error=True, content=[TextContent(type="text",
        text=json.dumps({"accepted": False, "error": "approval_required"}))])


class NetToolsClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    async def search(self, query: str, top_k: int=5) -> dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/search",
                json={
                    "query": query,
                    "top_k": top_k,
                }

            )

            response.raise_for_status()
            return response.json()

    async def create_jira_ticket(
        self, subject: str, description: str, project_key: str | None = None,
        issue_type: str | None = None, priority: str | None = None,
        labels: list[str] | None = None,
    ) -> dict:
        return deny_jira_write()

    async def update_jira_ticket(
        self, ticket_key: str, comment: str,
    ) -> dict:
        return deny_jira_write()

    async def search_jira_tickets(
        self, jql: str, max_results: int = 20, next_page_token: str | None = None,
    ) -> dict:
        return await self._jira_request("POST", "/api/v1/jira/search", {
            "jql": jql, "max_results": max_results, "next_page_token": next_page_token,
        })

    async def _jira_request(self, method: str, path: str, payload: dict) -> dict:
        if method != "POST" or path != "/api/v1/jira/search":
            return deny_jira_write()
        async with httpx.AsyncClient(timeout=40.0) as client:
            response = await client.request(method, f"{self.base_url.rstrip('/')}{path}", json=payload)
            response.raise_for_status()
            return response.json()

    async def close_ticket(self, ticket_id: str) -> dict:
        return deny_jira_write()
        