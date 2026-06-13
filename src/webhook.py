from fastapi import APIRouter, Request, HTTPException, BackgroundTasks

router = APIRouter()


def verify_token(request: Request, expected_token: str) -> None:
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if token != expected_token:
        raise HTTPException(status_code=401, detail="invalid token")


async def run_pipeline(payload: dict, graph, initial_state: dict) -> None:
    config = {"configurable": {"payload": payload}}
    await graph.ainvoke(initial_state, config)
