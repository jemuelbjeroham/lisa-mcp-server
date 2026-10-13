
import os

import httpx


class InternetClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["TAVILY_API_KEY"]
        self.base_url = "https://api.tavily.com"

    async def search(
        self,
        query: str,
        count: int = 5,
        fetch: bool = False,
    ) -> dict:
        payload = {
            "query": query,
            "topic": "general",
            "search_depth": "basic",
            "max_results": count,
            "include_raw_content": fetch,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/search",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json()
