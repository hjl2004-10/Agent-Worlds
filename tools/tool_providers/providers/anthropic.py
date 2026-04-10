# ============================================
# tools/tool/providers/anthropic.py - Anthropic 原生工具调用协议
# 职责: 实现 Anthropic API 级别的 tool_use
# ============================================

from typing import Any, Dict, List, Optional

from tools.tool_providers.providers.base import BaseToolProvider


class AnthropicProvider(BaseToolProvider):
    """
    Anthropic 原生工具调用协议

    触发方式: LLM 返回 content block 中 type="tool_use"
    需要: 在调用 LLM 时传入 tools 定义
    """

    @property
    def name(self) -> str:
        return "anthropic"

    def get_tool_definitions(self, tools: List[Dict]) -> List[Dict]:
        """
        将工具注册转换为 Anthropic tools 格式

        Args:
            tools: 工具注册列表 [{"name": ..., "description": ..., "input_schema": ..., ...}, ...]

        Returns:
            Anthropic tools 数组
        """
        definitions = []
        for tool in tools:
            # 检查是否有 Anthropic 格式的定义
            if "input_schema" in tool:
                definitions.append({
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("input_schema"),
                })
        return definitions

    def detect_trigger(self, response: Any, tools: List[Dict]) -> List[Dict]:
        """
        从 Anthropic 响应中检测 tool_use

        Args:
            response: Anthropic 响应对象或字典
            tools: 工具注册列表

        Returns:
            检测到的工具调用列表
        """
        results = []

        # 获取 content blocks
        content = self._get_content(response)
        if not content:
            return []

        for block in content:
            block_type = self._get_block_type(block)
            if block_type == "tool_use":
                tool_name = self._get_block_attr(block, "name")
                tool_input = self._get_block_attr(block, "input", {})
                tool_id = self._get_block_attr(block, "id")

                results.append({
                    "name": tool_name,
                    "id": tool_id,
                    "input": tool_input,
                    "raw_block": block,
                })

        return results

    def execute(self, tool_call: Dict, handler: callable, npc: Any, context: Dict) -> Any:
        """
        执行工具处理函数

        Args:
            tool_call: {"name": ..., "input": ..., "id": ...}
            handler: 处理函数 handler(input_dict, npc, context)
            npc: NPC 对象
            context: 上下文

        Returns:
            执行结果
        """
        tool_input = tool_call.get("input", {})
        return handler(tool_input, npc, context)

    def format_result(self, tool_call: Dict, result: Any) -> Dict:
        """
        格式化为 Anthropic tool_result 格式

        Args:
            tool_call: 原始工具调用
            result: 执行结果

        Returns:
            tool_result block
        """
        content = result
        if not isinstance(result, str):
            content = str(result)

        return {
            "type": "tool_result",
            "tool_use_id": tool_call.get("id"),
            "content": content,
        }

    # ========== 内部方法 ==========

    def _get_content(self, response: Any) -> Optional[List]:
        """从响应中获取 content 列表"""
        if response is None:
            return None

        # 字典格式
        if isinstance(response, dict):
            return response.get("content")

        # SDK 对象格式
        if hasattr(response, "content"):
            return response.content

        return None

    def _get_block_type(self, block: Any) -> Optional[str]:
        """获取 block 类型"""
        if isinstance(block, dict):
            return block.get("type")
        if hasattr(block, "type"):
            return block.type
        return None

    def _get_block_attr(self, block: Any, attr: str, default: Any = None) -> Any:
        """获取 block 属性"""
        if isinstance(block, dict):
            return block.get(attr, default)
        if hasattr(block, attr):
            return getattr(block, attr, default)
        return default
