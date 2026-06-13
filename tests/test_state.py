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
