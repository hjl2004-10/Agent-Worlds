# ============================================
# tools/tool/providers/__init__.py - 工具协议提供者注册
# ============================================

from tools.tool_providers.providers.base import BaseToolProvider
from tools.tool_providers.providers.custom import CustomProvider
from tools.tool_providers.providers.anthropic import AnthropicProvider

# 提供者注册表
PROVIDERS = {
    "custom": CustomProvider(),
    "anthropic": AnthropicProvider(),
}


def get_provider(name: str) -> BaseToolProvider:
    """获取工具协议提供者"""
    if name not in PROVIDERS:
        raise ValueError(f"Unknown tool provider: {name}")
    return PROVIDERS[name]


def list_providers() -> list:
    """列出所有可用的提供者"""
    return list(PROVIDERS.keys())
