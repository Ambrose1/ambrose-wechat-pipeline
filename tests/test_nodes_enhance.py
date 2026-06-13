from unittest.mock import MagicMock
from src.nodes.enhance import enhance_node


def test_enhance_node_adds_sections():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="引言段落\n\n正文内容\n\n总结与CTA")

    state = {
        "title": "文章标题",
        "polished": "这是润色后的文章内容",
        "metadata": {},
    }
    result = enhance_node(state, mock_llm)

    assert result["enhanced"] == "引言段落\n\n正文内容\n\n总结与CTA"
    mock_llm.invoke.assert_called_once()
    call_arg = mock_llm.invoke.call_args[0][0]
    assert "文章标题" in str(call_arg)
    assert "润色后的文章内容" in str(call_arg)
    assert "引言" in str(call_arg).lower() or "小标题" in str(call_arg).lower()


def test_enhance_node_returns_error_on_llm_failure():
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("API 超时")

    state = {
        "title": "标题",
        "polished": "内容",
        "metadata": {},
    }
    result = enhance_node(state, mock_llm)

    assert "error" in result
    assert result["enhanced"] == ""
