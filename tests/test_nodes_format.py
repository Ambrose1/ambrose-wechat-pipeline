from src.nodes.format import format_node


def test_format_node_converts_markdown_headers():
    state = {
        "title": "文章标题",
        "enhanced": "## 引言\n\n这是内容。\n\n### 小节\n\n更多内容。",
        "metadata": {},
    }
    result = format_node(state)

    assert "<h2" in result["formatted"] or "<section" in result["formatted"]
    assert "引言" in result["formatted"]
    assert "这是内容" in result["formatted"]


def test_format_node_wraps_paragraphs():
    state = {
        "title": "标题",
        "enhanced": "第一段内容。\n\n第二段内容。\n\n第三段内容。",
        "metadata": {},
    }
    result = format_node(state)

    assert result["formatted"].count("<p") >= 2 or result["formatted"].count("<br") >= 2
    assert "第一段内容" in result["formatted"]


def test_format_node_preserves_title():
    state = {
        "title": "我的文章标题",
        "enhanced": "一些内容",
        "metadata": {"source": "coze"},
    }
    result = format_node(state)

    assert result["title"] == "我的文章标题"
    assert result["metadata"]["source"] == "coze"
