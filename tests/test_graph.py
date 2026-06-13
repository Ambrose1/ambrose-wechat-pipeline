from unittest.mock import MagicMock, AsyncMock
from src.graph import build_graph
from src.state import PipelineState


def test_graph_has_all_nodes():
    mock_llm = MagicMock()
    mock_wechat = AsyncMock()
    graph = build_graph(mock_llm, mock_wechat)
    node_names = list(graph.nodes.keys())

    for name in ["receive", "polish", "enhance", "format", "upload", "log"]:
        assert name in node_names, f"缺少节点: {name}"


def test_graph_compiles():
    mock_llm = MagicMock()
    mock_wechat = AsyncMock()
    graph = build_graph(mock_llm, mock_wechat)
    app = graph.compile()
    assert app is not None


def test_graph_entry_point_is_receive():
    mock_llm = MagicMock()
    mock_wechat = AsyncMock()
    graph = build_graph(mock_llm, mock_wechat)
    # langgraph 0.6.x stores entry point as an edge from __start__
    assert ("__start__", "receive") in graph.edges, (
        "入口节点应为 receive"
    )
