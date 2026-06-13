import pytest
from unittest.mock import AsyncMock
from src.nodes.upload import upload_node


@pytest.mark.asyncio
async def test_upload_node_calls_client():
    mock_client = AsyncMock()
    mock_client.add_draft.return_value = "draft_media_123"

    state = {
        "title": "最终标题",
        "formatted": "<p>排版后的内容</p>",
        "metadata": {"source": "coze"},
    }
    result = await upload_node(state, mock_client)

    assert result["draft_media_id"] == "draft_media_123"
    mock_client.add_draft.assert_called_once_with(
        title="最终标题",
        content="<p>排版后的内容</p>",
    )


@pytest.mark.asyncio
async def test_upload_node_handles_failure():
    mock_client = AsyncMock()
    mock_client.add_draft.side_effect = RuntimeError("微信 API 限流")

    state = {
        "title": "标题",
        "formatted": "<p>内容</p>",
        "metadata": {},
    }
    result = await upload_node(state, mock_client)

    assert "error" in result
    assert "微信 API 限流" in result["error"]
    assert result["draft_media_id"] == ""
