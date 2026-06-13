from typing import Optional

from src.state import PipelineState


def receive_node(state: PipelineState, payload: dict) -> dict:
    """解析 Coze webhook payload，提取标题和正文。校验失败时返回 error。"""
    title = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()

    if not title:
        return {"error": "title is required"}
    if not content:
        return {"error": "content is required"}

    return {
        "title": title,
        "content": content,
        "metadata": {
            "agent_id": payload.get("agent_id", ""),
            "timestamp": payload.get("timestamp", ""),
            "source": "coze",
        },
    }
