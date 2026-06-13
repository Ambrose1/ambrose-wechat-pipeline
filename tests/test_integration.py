import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport, AsyncClient
from src.main import create_app


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.invoke.side_effect = [
        MagicMock(content="润色后的文章"),
        MagicMock(content="引言\n\n润色后的文章\n\n总结\n\nCTA"),
    ]
    return llm


@pytest.fixture
def mock_upload():
    """mock playwright upload"""
    with patch("src.nodes.upload._get_page") as mock:
        mock_page = AsyncMock()
        mock_page.is_closed.return_value = False
        mock_new_page = AsyncMock()
        mock_page.context.new_page.return_value = mock_new_page

        mock_title_input = AsyncMock()
        mock_body = AsyncMock()
        mock_frame = AsyncMock()
        mock_frame.return_value = mock_body

        mock_new_page.locator.side_effect = lambda sel: {
            "#title": mock_title_input,
            "#ueditor_0": mock_frame,
        }.get(sel, AsyncMock())
        mock_new_page.frame_locator.return_value = mock_frame

        mock.return_value = mock_page
        yield mock


@pytest.fixture
def app(mock_llm):
    return create_app(llm=mock_llm, webhook_token="integration-token")


@pytest.mark.asyncio
async def test_full_pipeline(mock_llm, mock_upload, app):
    """端到端流程：webhook 接收 → 润色 → 补充 → 排版 → 上传 → 记录"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/webhook/coze",
            json={
                "title": "AI 如何改变我们的生活",
                "content": "人工智能正在深刻改变我们生活的方方面面...",
                "agent_id": "coze-agent-42",
                "timestamp": "2026-06-13T08:00:00Z",
            },
            headers={"Authorization": "Bearer integration-token"},
        )
    assert resp.status_code == 202
    assert resp.json() == {"status": "accepted"}

    await asyncio.sleep(0.2)

    assert mock_llm.invoke.call_count == 2
    assert mock_upload.called


@pytest.mark.asyncio
async def test_pipeline_with_invalid_input(mock_llm, mock_upload, app):
    """无效输入不应该崩溃"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/webhook/coze",
            json={"unexpected": "field"},
            headers={"Authorization": "Bearer integration-token"},
        )
    assert resp.status_code == 202
