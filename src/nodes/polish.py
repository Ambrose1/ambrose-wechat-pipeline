from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

POLISH_SYSTEM_PROMPT = """你是一位专业的微信公众号编辑。请根据用户指定的风格对文章进行润色：

风格说明：
- 深度：保持专业深度，使用更精准的词汇，段落之间逻辑紧密
- 轻松：语气亲切口语化，适当使用生活化比喻，段落短小易读
- 干货：信息密度高，分点清晰，去掉冗余修辞

要求：
1. 保留原文的核心观点和结构
2. 不要添加原文没有的事实信息
3. 只返回润色后的全文，不要解释你做了什么"""


def polish_node(state: dict, llm: BaseChatModel, style: str = "深度") -> dict:
    title = state.get("title", "")
    content = state.get("content", "")

    messages = [
        SystemMessage(content=POLISH_SYSTEM_PROMPT),
        HumanMessage(content=f"标题：{title}\n\n正文：\n{content}\n\n请用「{style}」风格润色这篇公众号文章。"),
    ]
    response = llm.invoke(messages)

    return {
        "title": title,
        "polished": response.content,
        "metadata": state.get("metadata", {}),
    }
