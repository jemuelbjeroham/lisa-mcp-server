from unittest.mock import AsyncMock, MagicMock

import pytest

from lisa_mcp_server.net_tools_client import NetToolsClient


@pytest.mark.asyncio
async def test_knowledge_client_preserves_grouped_evidence_and_all_fifteen_results(monkeypatch):
    payload = {"context": "## Text\nText evidence\n## OCR\nOCR evidence\n## Macros\nMacro evidence\n## Source URLs\nhttps://example.com/page",
        "results": [{"content": f"Chunk {index}"} for index in range(15)], "citations": []}
    response = MagicMock()
    response.json.return_value = payload
    transport = AsyncMock()
    transport.post.return_value = response
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=transport)
    manager.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=manager)
    monkeypatch.setattr("lisa_mcp_server.net_tools_client.httpx.AsyncClient", factory)
    result = await NetToolsClient("http://tools").search("routing", top_k=5)
    factory.assert_called_once_with(timeout=60.0)
    transport.post.assert_awaited_once_with("http://tools/api/v1/search", json={"query": "routing", "top_k": 5})
    response.raise_for_status.assert_called_once()
    assert result is payload
    assert len(result["results"]) == 15