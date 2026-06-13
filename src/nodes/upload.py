from src.wechat import WeChatClient


async def upload_node(state: dict, client: WeChatClient) -> dict:
    """上传文章到微信公众号草稿箱。"""
    title = state.get("title", "")
    formatted = state.get("formatted", "")

    try:
        media_id = await client.add_draft(title=title, content=formatted)
        return {"draft_media_id": media_id}
    except Exception as e:
        return {"draft_media_id": "", "error": f"upload failed: {e}"}
