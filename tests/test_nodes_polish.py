from unittest.mock import MagicMock
from src.nodes.polish import polish_node
from src.state import PipelineState


def test_polish_node_calls_llm_with_correct_prompt():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="润色后的文章内容")

    state = PipelineState(
        title="一篇好文章",
        content="原始正文内容，需要润色。",
        polished="",
        enhanced="",
        formatted="",
        draft_media_id="",
        metadata={"source": "coze"},
    )
    result = polish_node(state, mock_llm, style="深度")

    assert result["polished"] == "润色后的文章内容"
    mock_llm.invoke.assert_called_once()
    call_arg = mock_llm.invoke.call_args[0][0]
    assert "一篇好文章" in str(call_arg)
    assert "原始正文" in str(call_arg)
    assert "深度" in str(call_arg)


def test_polish_node_preserves_other_fields():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="done")

    state = PipelineState(
        title="标题",
        content="正文",
        polished="",
        enhanced="",
        formatted="",
        draft_media_id="",
        metadata={"source": "coze"},
    )
    result = polish_node(state, mock_llm, style="轻松")

    assert result["title"] == "标题"
    assert result["metadata"]["source"] == "coze"
    assert "error" not in result
