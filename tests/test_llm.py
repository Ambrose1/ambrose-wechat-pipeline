import os
import pytest
from src.llm import create_llm, LLMConfig


def test_create_llm_requires_api_key():
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        create_llm(LLMConfig(provider="openai", model="gpt-4o", api_key=""))


def test_create_llm_unsupported_provider():
    with pytest.raises(ValueError, match="unsupported|不支持"):
        create_llm(LLMConfig(provider="unknown", model="x", api_key="sk-test"))


def test_create_openai_llm():
    os.environ["OPENAI_API_KEY"] = "sk-test"
    llm = create_llm(LLMConfig(provider="openai", model="gpt-4o", api_key="sk-test"))
    assert "gpt-4o" in str(llm.model_name)


def test_llm_config_defaults():
    cfg = LLMConfig(provider="openai", model="gpt-4o-mini", api_key="sk-test")
    assert cfg.base_url is None
    assert cfg.temperature == 0.7


def test_llm_config_repr_masks_api_key():
    cfg = LLMConfig(provider="openai", model="gpt-4o", api_key="sk-1234567890abcdef")
    r = repr(cfg)
    assert "sk-1***" in r
    assert "1234567890abcdef" not in r


def test_create_claude_llm():
    llm = create_llm(LLMConfig(provider="claude", model="claude-sonnet-4-6", api_key="sk-ant-test"))
    assert "claude" in str(llm).lower()
