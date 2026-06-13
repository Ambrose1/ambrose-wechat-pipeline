from dataclasses import dataclass
from typing import Optional
from langchain_core.language_models import BaseChatModel


@dataclass
class LLMConfig:
    provider: str          # openai | claude | deepseek | qwen
    model: str
    api_key: str
    base_url: Optional[str] = None
    temperature: float = 0.7

    def __repr__(self) -> str:
        return (
            f"LLMConfig(provider={self.provider!r}, model={self.model!r}, "
            f"api_key='{self.api_key[:4]}***', base_url={self.base_url!r}, "
            f"temperature={self.temperature})"
        )


def create_llm(config: LLMConfig) -> BaseChatModel:
    if not config.api_key:
        raise ValueError("LLM_API_KEY 不能为空")

    provider = config.provider.lower()

    if provider in ("openai", "deepseek", "qwen"):
        from langchain_openai import ChatOpenAI
        kwargs = dict(model=config.model, api_key=config.api_key, temperature=config.temperature)
        if config.base_url:
            kwargs["base_url"] = config.base_url
        return ChatOpenAI(**kwargs)

    if provider == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=config.model,
            api_key=config.api_key,
            temperature=config.temperature,
        )

    raise ValueError(f"不支持的 LLM provider: {config.provider}")
