import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from src.llm import create_llm, LLMConfig
from src.graph import build_graph
from src.state import PipelineState
from src.webhook import verify_token, run_pipeline

load_dotenv()


def create_app(llm=None, webhook_token=None):
    app = FastAPI(title="WeChat Pipeline")

    _token = webhook_token or os.getenv("WEBHOOK_TOKEN", "")
    _llm = llm or create_llm(LLMConfig(
        provider=os.getenv("LLM_PROVIDER", "openai"),
        model=os.getenv("LLM_MODEL", "gpt-4o"),
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL") or None,
    ))
    _style = os.getenv("ARTICLE_STYLE", "深度")
    _graph = build_graph(_llm, style=_style).compile()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/webhook/coze")
    async def webhook_coze(request: Request, background_tasks: BackgroundTasks):
        verify_token(request, _token)
        payload = await request.json()

        initial_state = PipelineState(
            title="",
            content="",
            polished="",
            enhanced="",
            formatted="",
            draft_media_id="",
            metadata={},
        )

        background_tasks.add_task(run_pipeline, payload, _graph, initial_state)
        return JSONResponse(status_code=202, content={"status": "accepted"})

    return app


try:
    app = create_app()
except ValueError:
    app = None
