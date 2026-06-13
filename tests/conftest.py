import pytest
import os


@pytest.fixture(autouse=True)
def clean_env():
    """每个测试前清理相关环境变量，避免测试间互相影响。"""
    keys = [
        "LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY", "LLM_BASE_URL",
        "WECHAT_APP_ID", "WECHAT_APP_SECRET", "WEBHOOK_TOKEN",
    ]
    saved = {k: os.environ.pop(k, None) for k in keys}
    yield
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)
