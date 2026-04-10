# ============================================
# tools/tool/providers/base.py - 工具协议基类
# 职责: 定义工具协议适配器的统一接口
# ============================================

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseToolProvider(ABC):
    """
    工具协议提供者基类

    不同的提供者实现不同的工具调用协议:
    - custom: 自定义文本触发 (【工具:xxx】)
    - anthropic: Anthropic 原生 tool_use
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """提供者名称"""
        pass

    @abstractmethod
    def get_tool_definitions(self, tools: List[Dict]) -> Any:
        """
        返回发给 LLM 的工具定义格式

        Args:
            tools: 工具注册列表 [{"name": ..., "handler": ..., ...}, ...]

        Returns:
            格式化后的工具定义 (不同协议格式不同)
            - custom: 返回 None (不需要发给 LLM)
            - anthropic: 返回 tools 数组
        """
        pass

    @abstractmethod
    def detect_trigger(self, response: Any, tools: List[Dict]) -> List[Dict]:
        """
        从 LLM 响应中检测工具调用

        Args:
            response: LLM 的响应 (可能是字符串或对象)
            tools: 工具注册列表

        Returns:
            检测到的工具调用列表 [{"name": ..., "input": ..., ...}, ...]
        """
        pass

    @abstractmethod
    def execute(self, tool_call: Dict, handler: callable, npc: Any, context: Dict) -> Any:
        """
        执行工具调用

        Args:
            tool_call: 工具调用信息
            handler: 工具处理函数
            npc: 触发工具的 NPC
            context: 上下文 {"response": ..., "listener": ...}

        Returns:
            执行结果
        """
        pass

    @abstractmethod
    def format_result(self, tool_call: Dict, result: Any) -> Any:
        """
        格式化工具执行结果 (用于返回给 LLM)

        Args:
            tool_call: 工具调用信息
            result: 执行结果

        Returns:
            格式化后的结果
        """
        pass
