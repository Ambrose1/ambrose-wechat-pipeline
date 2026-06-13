import pytest
from unittest.mock import AsyncMock, patch
from src.nodes.upload import upload_node


@pytest.mark.asyncio
async def test_upload_node_empty_title():
    state = {
        "title": "",
        "formatted": "<p>内容</p>",
        "metadata": {},
    }
    result = await upload_node(state)
    assert "error" in result
    assert result["draft_media_id"] == ""


@pytest.mark.asyncio
async def test_upload_node_empty_formatted():
    state = {
        "title": "标题",
        "formatted": "",
        "metadata": {},
    }
    result = await upload_node(state)
    assert "error" in result
    assert result["draft_media_id"] == ""


@pytest.mark.asyncio
async def test_upload_node_with_mock():
    """模拟 Playwright 页面操作成功的情况。"""
    mock_page = AsyncMock()
    mock_page.is_closed.return_value = False
    mock_new_page = AsyncMock()
    mock_page.context.new_page.return_value = mock_new_page

    mock_title_input = AsyncMock()
    mock_body = AsyncMock()
    mock_frame_locator = AsyncMock()
    mock_frame_locator.return_value = mock_body

    mock_new_page.locator.side_effect = lambda sel: {
        "#title": mock_title_input,
        "#ueditor_0": mock_frame_locator,
    }.get(sel, AsyncMock())
    mock_new_page.frame_locator.return_value = mock_frame_locator

    state = {
        "title": "测试标题",
        "formatted": "<p>测试内容</p>",
        "metadata": {"source": "coze"},
    }

    with patch("src.nodes.upload._get_page", new=AsyncMock(return_value=mock_page)):
        result = await upload_node(state)

    assert result["draft_media_id"] == "saved"
    assert "error" not in result
