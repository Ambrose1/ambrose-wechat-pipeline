from src.nodes.receive import receive_node
from src.state import PipelineState


def test_receive_node_extracts_fields():
    state = PipelineState(
        title="",
        content="",
        polished="",
        enhanced="",
        formatted="",
        draft_media_id="",
        metadata={},
    )
    webhook_payload = {
        "title": "测试文章标题",
        "content": "这是 Coze Agent 产出的文章正文。",
        "agent_id": "agent-001",
        "timestamp": "2026-06-13T10:00:00Z",
    }
    result = receive_node(state, webhook_payload)
    assert result["title"] == "测试文章标题"
    assert result["content"] == "这是 Coze Agent 产出的文章正文。"
    assert result["metadata"]["agent_id"] == "agent-001"


def test_receive_node_rejects_empty_title():
    state = PipelineState(
        title="", content="", polished="", enhanced="",
        formatted="", draft_media_id="", metadata={},
    )
    result = receive_node(state, {"title": "", "content": "正文"})
    assert result["error"] is not None
    assert "title" in result["error"].lower()


def test_receive_node_rejects_empty_content():
    state = PipelineState(
        title="", content="", polished="", enhanced="",
        formatted="", draft_media_id="", metadata={},
    )
    result = receive_node(state, {"title": "标题", "content": ""})
    assert result["error"] is not None
    assert "content" in result["error"].lower()
