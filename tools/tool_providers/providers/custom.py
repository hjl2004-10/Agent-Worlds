# ============================================
# tools/tool/providers/custom.py - 自定义文本触发协议
# 职责: 实现【工具:xxx】等文本模式触发
# ============================================

import re
from typing import Any, Dict, List

from tools.tool_providers.providers.base import BaseToolProvider


class CustomProvider(BaseToolProvider):
    """
    自定义工具协议

    触发方式: AI 回复中包含特定文本模式
    例如: "【工具:测试】", "[group:朋友]"
    """

    @property
    def name(self) -> str:
        return "custom"

    def get_tool_definitions(self, tools: List[Dict]) -> Any:
        """
        自定义协议不需要发送工具定义给 LLM
        而是通过 tools_prompt 注入到 system prompt
        """
        return None

    def detect_trigger(self, response: Any, tools: List[Dict]) -> List[Dict]:
        """
        从文本中检测触发模式

        Args:
            response: 字符串 (AI 回复)
            tools: 工具注册列表 [{"trigger": ..., ...}, ...]

        Returns:
            检测到的工具调用列表
        """
        if not isinstance(response, str):
            return []

        text = response
        results = []

        for tool in tools:
            trigger = tool.get("trigger", "")
            if not trigger:
                continue

            match_result = self._match_trigger(text, trigger)
            if match_result:
                results.append({
                    "name": tool.get("name"),
                    "tool_id": tool.get("tool_id"),
                    "trigger": trigger,
                    "match_result": match_result,
                    "input": self._extract_input(match_result),
                })

        return results

    def execute(self, tool_call: Dict, handler: callable, npc: Any, context: Dict) -> Any:
        """
        执行工具处理函数

        Args:
            tool_call: {"match_result": ..., "input": ...}
            handler: 处理函数 handler(npc, match_result, context)
            npc: NPC 对象
            context: 上下文

        Returns:
            执行结果
        """
        match_result = tool_call.get("match_result")
        return handler(npc, match_result, context)

    def format_result(self, tool_call: Dict, result: Any) -> Any:
        """
        自定义协议不需要格式化结果返回给 LLM
        """
        return result

    # ========== 内部方法 ==========

    def _match_trigger(self, text: str, trigger: str):
        """
        匹配触发模式

        Args:
            text: 待匹配文本
            trigger: 触发模式
                - 普通字符串: 简单包含匹配
                - "re:xxx": 正则表达式匹配

        Returns:
            匹配结果:
                - 简单匹配: True
                - 正则匹配: match 对象
                - 未匹配: None
        """
        if not text or not trigger:
            return None

        # 正则模式: 以 "re:" 开头
        if trigger.startswith("re:"):
            pattern = trigger[3:]
            try:
                match = re.search(pattern, text)
                return match
            except re.error:
                return None

        # 简单包含匹配
        if trigger in text:
            return True

        return None

    def _extract_input(self, match_result) -> Any:
        """
        从匹配结果中提取输入参数

        Args:
            match_result: True 或 re.Match 对象

        Returns:
            提取的参数 (正则捕获组 或 None)
        """
        if match_result is True:
            return None
        if hasattr(match_result, 'groups'):
            groups = match_result.groups()
            return groups if groups else None
        return None
