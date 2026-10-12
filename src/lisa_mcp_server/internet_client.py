import httpx


class InternetClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def search(
            self,
            query: str,
            count: int=5,
            fetch: bool=False,
    ) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/search",
                params={
                    "q": query,
                    "count": count,
                    "fetch": fetch,
                },
            )

            response.raise_for_status()
            return response.json()
        


