import json
import tempfile
import os
from src.nodes.log import log_node


def test_log_node_writes_json_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "pipeline.log")
        state = {
            "title": "完成文章",
            "draft_media_id": "draft_001",
            "error": None,
            "metadata": {"source": "coze", "agent_id": "agent-1"},
        }
        result = log_node(state, log_path)

        assert result == {}  # 不修改 state
        assert os.path.exists(log_path)

        with open(log_path) as f:
            lines = f.readlines()
        entry = json.loads(lines[-1])
        assert entry["title"] == "完成文章"
        assert entry["draft_media_id"] == "draft_001"


def test_log_node_records_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "pipeline.log")
        state = {
            "title": "失败文章",
            "draft_media_id": "",
            "error": "upload failed: 网络超时",
            "metadata": {},
        }
        result = log_node(state, log_path)

        with open(log_path) as f:
            entry = json.loads(f.readlines()[-1])
        assert entry["error"] == "upload failed: 网络超时"
        assert entry["status"] == "failed"
