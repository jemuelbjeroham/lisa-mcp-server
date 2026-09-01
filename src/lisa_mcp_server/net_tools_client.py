import httpx


class NetToolsClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    async def search(self, query: str, top_k: int=5) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/search",
                json={
                    "query": query,
                    "top_k": top_k,
                }

            )

            response.raise_for_status()
            return response.json()
        