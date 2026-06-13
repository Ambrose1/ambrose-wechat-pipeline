import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport, AsyncClient
from src.main import create_app


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="润色/补充后的内容")
    return llm


@pytest.fixture
def app(mock_llm):
    with patch("src.nodes.upload._get_page", new=AsyncMock()):
        return create_app(llm=mock_llm, webhook_token="test-token")


@pytest.mark.asyncio
async def test_webhook_accepts_valid_request(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/webhook/coze",
            json={
                "title": "测试文章",
                "content": "这是正文内容",
                "agent_id": "agent-1",
                "timestamp": "2026-06-13T10:00:00Z",
            },
            headers={"Authorization": "Bearer test-token"},
        )
    assert resp.status_code == 202
    assert resp.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_token(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/webhook/coze",
            json={"title": "测试", "content": "内容"},
            headers={"Authorization": "Bearer wrong-token"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_check(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
