import json
import os
from datetime import datetime, timezone


def log_node(state: dict, log_path: str = "data/pipeline.log") -> dict:
    """记录流水线执行结果到 JSONL 日志文件。"""
    os.makedirs(os.path.dirname(log_path) or "data", exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "title": state.get("title", ""),
        "draft_media_id": state.get("draft_media_id", ""),
        "error": state.get("error"),
        "status": "failed" if state.get("error") else "success",
        "metadata": state.get("metadata", {}),
    }

    with open(log_path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {}
