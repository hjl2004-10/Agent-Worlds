# ============================================
# tools/llm/providers/claude.py - Claude适配器
# 职责: 适配 Anthropic Claude API
# ============================================

from typing import List, Dict, Any, Optional
from .base import BaseProvider


class ClaudeProvider(BaseProvider):
    """
    Anthropic Claude 适配器

    Claude API 格式与 OpenAI 不同:
    - 请求体需要 anthropic-version
    - system 消息单独放在顶层
    - 响应格式不同
    - 支持 tools 和 tool_use
    """

    @property
    def name(self) -> str:
        return "claude"

    def build_request(
        self,
        messages: List[Dict],
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.8,
        max_tokens: int = 200,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> tuple:
        """构建 Claude 格式请求"""

        # 请求地址
        url = f"{base_url}/v1/messages"

        # 请求头
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        # 分离 system 消息 (Claude 要求单独传)
        system_content = ""
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_content += msg["content"] + "\n"
            else:
                # 处理 content 可能是字符串或列表的情况
                content = msg.get("content")
                if isinstance(content, str):
                    chat_messages.append({
                        "role": msg["role"],
                        "content": content
                    })
                elif isinstance(content, list):
                    # 已经是 content blocks 格式
                    chat_messages.append({
                        "role": msg["role"],
                        "content": content
                    })

        # 请求体
        payload = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        # 如果有 system 消息，添加到顶层
        if system_content.strip():
            payload["system"] = system_content.strip()

        # 如果有工具定义，添加到请求
        if tools:
            payload["tools"] = tools

        return url, headers, payload

    def parse_response(self, response_data: dict) -> str:
        """解析 Claude 格式响应 (只返回文本)"""
        result = self.parse_response_with_tools(response_data)
        return result.get("text", "")

    def parse_response_with_tools(self, response_data: dict) -> Dict:
        """
        解析 Claude 格式响应 (返回完整信息)

        Returns:
            Dict: {
                "text": 文本内容,
                "has_tool_use": bool,
                "tool_uses": [...],
                "content_blocks": [...],
                "stop_reason": str
            }
        """
        try:
            content = response_data.get("content", [])
            stop_reason = response_data.get("stop_reason", "")

            text_parts = []
            tool_uses = []
            has_tool_use = False

            for block in content:
                block_type = block.get("type")

                if block_type == "text":
                    text_parts.append(block.get("text", ""))

                elif block_type == "tool_use":
                    has_tool_use = True
                    tool_uses.append({
                        "id": block.get("id"),
                        "name": block.get("name"),
                        "input": block.get("input", {}),
                        "raw_block": block
                    })

            # 组合文本
            text = "".join(text_parts)

            return {
                "text": text,
                "has_tool_use": has_tool_use,
                "tool_uses": tool_uses,
                "content_blocks": content,
                "stop_reason": stop_reason
            }

        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Claude响应解析失败: {e}, 数据: {response_data}")
