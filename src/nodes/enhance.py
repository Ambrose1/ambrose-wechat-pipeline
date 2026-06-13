from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

ENHANCE_SYSTEM_PROMPT = """你是一位微信公众号内容策划。请对以下文章进行板块补充：

必须添加以下板块（如原文已有则优化）：
1. **引言**（2-3句，点出读者痛点或好奇心钩子）
2. **小标题**（为每个主要段落添加吸引人的小标题）
3. **总结**（1-2句精炼收尾）
4. **CTA**（引导读者点赞/在看/转发）

要求：
- 保持文章原有内容不变，只添加缺失的板块
- 小标题用 **加粗** 标记
- 不要改变原文的事实信息
- 只返回补充后的完整文章"""


def enhance_node(state: dict, llm: BaseChatModel) -> dict:
    title = state.get("title", "")
    polished = state.get("polished", "")

    try:
        messages = [
            SystemMessage(content=ENHANCE_SYSTEM_PROMPT),
            HumanMessage(content=f"标题：{title}\n\n文章内容：\n{polished}\n\n请补充缺失的板块。"),
        ]
        response = llm.invoke(messages)
        return {"enhanced": response.content}
    except Exception as e:
        return {"enhanced": "", "error": f"enhance failed: {e}"}
