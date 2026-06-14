import pytest
from unittest.mock import AsyncMock, patch
from src.nodes.upload import upload_node


@pytest.mark.asyncio
async def test_upload_node_empty_title():
    state = {"title": "", "formatted": "<p>内容</p>", "metadata": {}}
    result = await upload_node(state)
    assert "error" in result
    assert result["draft_media_id"] == ""


@pytest.mark.asyncio
async def test_upload_node_empty_formatted():
    state = {"title": "标题", "formatted": "", "metadata": {}}
    result = await upload_node(state)
    assert "error" in result
    assert result["draft_media_id"] == ""


@pytest.mark.asyncio
async def test_upload_node_with_mock():
    """模拟完整流程。"""
    mock_editor = AsyncMock()
    mock_editor.url = "https://mp.weixin.qq.com/cgi-bin/appmsg?..."
    mock_editor.text_content.return_value = ""
    mock_editor.wait_for_load_state.return_value = None

    mock_title = AsyncMock()
    mock_title.count.return_value = 1
    mock_title.is_visible.return_value = True
    mock_editor.locator.return_value = mock_title

    mock_frame = AsyncMock()
    mock_body = AsyncMock()
    mock_body.count.return_value = 1
    mock_frame.return_value = mock_body
    mock_editor.frame_locator.return_value = mock_frame

    mock_btn = AsyncMock()
    mock_btn.count.return_value = 1
    mock_btn.is_visible.return_value = True
    mock_editor.locator.return_value = mock_btn

    state = {"title": "测试标题", "formatted": "<p>测试内容</p>", "metadata": {"source": "coze"}}

    with patch("src.nodes.upload._get_page", new=AsyncMock()), \
         patch("src.nodes.upload._open_editor", new=AsyncMock(return_value=mock_editor)):
        result = await upload_node(state)

    assert result["draft_media_id"] == "saved"
    assert "error" not in result
