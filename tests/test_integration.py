import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient
from src.main import create_app


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    # 模拟 LLM 返回润色和补充后的内容
    llm.invoke.side_effect = [
        MagicMock(content="润色后的文章"),
        MagicMock(content="引言\n\n润色后的文章\n\n总结\n\nCTA"),
    ]
    return llm


@pytest.fixture
def mock_wechat():
    client = AsyncMock()
    client.add_draft.return_value = "draft_media_integration_test"
    return client


@pytest.fixture
def app(mock_llm, mock_wechat):
    return create_app(llm=mock_llm, wechat=mock_wechat, webhook_token="integration-token")


@pytest.mark.asyncio
async def test_full_pipeline(mock_llm, mock_wechat, app):
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

    # 等待后台任务完成
    await asyncio.sleep(0.1)

    # 验证 LLM 被调用了（润色 + 补充）
    assert mock_llm.invoke.call_count == 2

    # 验证微信上传被调用
    mock_wechat.add_draft.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_with_invalid_input(mock_llm, mock_wechat, app):
    """无效输入不应该崩溃"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/webhook/coze",
            json={"unexpected": "field"},
            headers={"Authorization": "Bearer integration-token"},
        )
    assert resp.status_code == 202
