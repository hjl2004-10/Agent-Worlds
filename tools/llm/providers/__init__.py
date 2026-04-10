# tools/llm/providers/ - LLM厂商适配器
from .base import BaseProvider
from .openai import OpenAIProvider
from .claude import ClaudeProvider

# 厂商注册表
PROVIDERS = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
}


def get_provider(name: str) -> BaseProvider:
    """获取适配器实例"""
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {name}")
    return PROVIDERS[name]()
