import re


def format_node(state: dict) -> dict:
    """将增强后的文章转换为微信兼容的 HTML 格式。"""
    content = state.get("enhanced", "")

    # 处理 Markdown 标题 (## → <h2>, ### → <h3>)
    content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
    content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)

    # 处理加粗 **text** → <strong>text</strong>
    content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)

    # 将空行分隔的文本块包裹为段落
    blocks = content.split('\n\n')
    formatted_blocks = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # 已含 HTML 标签的行不包裹
        if block.startswith('<h') or block.startswith('<section') or block.startswith('<p'):
            formatted_blocks.append(block)
        else:
            # 处理块内换行为 <br>
            inner = block.replace('\n', '<br>')
            formatted_blocks.append(f"<p>{inner}</p>")

    return {
        "title": state.get("title", ""),
        "formatted": "\n".join(formatted_blocks),
        "metadata": state.get("metadata", {}),
    }
