from langgraph.graph import StateGraph, END
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from src.state import PipelineState
from src.nodes.receive import receive_node
from src.nodes.polish import polish_node
from src.nodes.enhance import enhance_node
from src.nodes.format import format_node
from src.nodes.upload import upload_node
from src.nodes.log import log_node
from src.wechat import WeChatClient


def build_graph(llm: BaseChatModel, wechat: WeChatClient, style: str = "深度"):
    graph = StateGraph(PipelineState)

    def _receive(state: PipelineState, config: RunnableConfig) -> dict:
        payload = config.get("configurable", {}).get("payload", {})
        return receive_node(state, payload)

    def _polish(state: PipelineState) -> dict:
        return polish_node(state, llm, style=style)

    def _enhance(state: PipelineState) -> dict:
        return enhance_node(state, llm)

    def _format(state: PipelineState) -> dict:
        return format_node(state)

    async def _upload(state: PipelineState) -> dict:
        return await upload_node(state, wechat)

    def _log(state: PipelineState) -> dict:
        return log_node(state)

    graph.add_node("receive", _receive)
    graph.add_node("polish", _polish)
    graph.add_node("enhance", _enhance)
    graph.add_node("format", _format)
    graph.add_node("upload", _upload)
    graph.add_node("log", _log)

    graph.set_entry_point("receive")

    # 条件边：receive 出错直接跳 log
    def after_receive(state: PipelineState) -> str:
        if state.get("error"):
            return "log"
        return "polish"

    graph.add_conditional_edges("receive", after_receive, {"polish": "polish", "log": "log"})
    graph.add_edge("polish", "enhance")
    graph.add_edge("enhance", "format")
    graph.add_edge("format", "upload")
    graph.add_edge("upload", "log")
    graph.add_edge("log", END)

    return graph
