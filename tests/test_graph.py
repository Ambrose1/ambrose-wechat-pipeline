from unittest.mock import MagicMock
from src.graph import build_graph


def test_graph_has_all_nodes():
    mock_llm = MagicMock()
    graph = build_graph(mock_llm)
    node_names = list(graph.nodes.keys())

    for name in ["receive", "polish", "enhance", "format", "upload", "log"]:
        assert name in node_names, f"缺少节点: {name}"


def test_graph_compiles():
    mock_llm = MagicMock()
    graph = build_graph(mock_llm)
    app = graph.compile()
    assert app is not None


def test_graph_entry_point_is_receive():
    mock_llm = MagicMock()
    graph = build_graph(mock_llm)
    assert ("__start__", "receive") in graph.edges
