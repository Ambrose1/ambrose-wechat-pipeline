from src.state import PipelineState


def test_pipeline_state_fields():
    state = PipelineState(
        title="",
        content="",
        polished="",
        enhanced="",
        formatted="",
        draft_media_id="",
        error=None,
        metadata={},
    )
    assert state["title"] == ""
    assert state["error"] is None
    assert isinstance(state["metadata"], dict)


def test_pipeline_state_mutation():
    state = PipelineState(
        title="一篇好文章",
        content="原始内容",
        polished="",
        enhanced="",
        formatted="",
        draft_media_id="",
        error=None,
        metadata={"source": "coze"},
    )
    state["polished"] = "润色后内容"
    assert state["polished"] == "润色后内容"
    assert state["metadata"]["source"] == "coze"


def test_pipeline_state_without_error():
    """NotRequired 字段可省略。"""
    state = PipelineState(
        title="标题",
        content="内容",
        polished="",
        enhanced="",
        formatted="",
        draft_media_id="",
        metadata={},
    )
    assert "error" not in state
    assert state["title"] == "标题"


def test_pipeline_state_with_error():
    """error 字段可赋值并读取。"""
    state = PipelineState(
        title="失败文章",
        content="内容",
        polished="",
        enhanced="",
        formatted="",
        draft_media_id="",
        error="upload failed: 网络超时",
        metadata={},
    )
    assert state["error"] == "upload failed: 网络超时"
