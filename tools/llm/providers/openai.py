# ============================================
# tools/llm/providers/openai.py - OpenAI兼容适配器
# 职责: 适配 OpenAI/DeepSeek/通义千问 等兼容接口
# ============================================

from typing import List, Dict, Optional
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """
    OpenAI 兼容格式适配器

    支持:
    - OpenAI GPT 系列
    - DeepSeek
    - 通义千问 (Qwen)
    - 其他 OpenAI 兼容接口

    注意: OpenAI 的 tool_use 格式与 Anthropic 不同
    """

    @property
    def name(self) -> str:
        return "openai"

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
        """构建 OpenAI 兼容格式请求"""

        # 请求地址
        url = f"{base_url}/v1/chat/completions"

        # 请求头
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # 请求体
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # 额外参数
        if kwargs.get("stream"):
            payload["stream"] = kwargs["stream"]

        # 工具定义 (OpenAI 格式)
        if tools:
            # OpenAI 使用 functions 格式或 tools 格式
            # 这里转换为 OpenAI 的 tools 格式
            openai_tools = []
            for tool in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {})
                    }
                })
            payload["tools"] = openai_tools

        return url, headers, payload

    def parse_response(self, response_data: dict) -> str:
        """解析 OpenAI 格式响应 (只返回文本)"""
        result = self.parse_response_with_tools(response_data)
        return result.get("text", "")

    def parse_response_with_tools(self, response_data: dict) -> Dict:
        """
        解析 OpenAI 格式响应 (返回完整信息)

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
            choices = response_data.get("choices", [])
            if not choices:
                return {
                    "text": "",
                    "has_tool_use": False,
                    "tool_uses": [],
                    "content_blocks": [],
                    "stop_reason": ""
                }

            choice = choices[0]
            message = choice.get("message", {})
            finish_reason = choice.get("finish_reason", "")

            # 提取文本
            text = message.get("content", "") or ""

            # 检查工具调用
            tool_calls = message.get("tool_calls", [])
            tool_uses = []
            has_tool_use = False

            if tool_calls:
                has_tool_use = True
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_uses.append({
                        "id": tc.get("id"),
                        "name": func.get("name"),
                        "input": func.get("arguments", {}),  # 可能是 JSON 字符串
                        "raw_block": tc
                    })

            # 构建 content_blocks (兼容格式)
            content_blocks = []
            if text:
                content_blocks.append({"type": "text", "text": text})
            for tu in tool_uses:
                content_blocks.append({
                    "type": "tool_use",
                    "id": tu["id"],
                    "name": tu["name"],
                    "input": tu["input"]
                })

            return {
                "text": text,
                "has_tool_use": has_tool_use,
                "tool_uses": tool_uses,
                "content_blocks": content_blocks,
                "stop_reason": finish_reason
            }

        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"OpenAI响应解析失败: {e}, 数据: {response_data}")
