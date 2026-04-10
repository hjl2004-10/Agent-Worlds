# ============================================
# tools/llm_l1.py - LLM业务层
# 职责: 渠道路由、请求发送、响应处理、请求限流
# ============================================

import time
import threading
import requests
from typing import List, Dict, Optional, Any

from tools import llm_l2 as l2
from tools.llm.providers import get_provider


# ========== 渠道限流器 ==========
# 每个渠道独立计时，用 Lock 保证线程安全

_rate_lock = threading.Lock()
_last_request_time: Dict[str, float] = {}  # {channel_name: timestamp}


TOOL_LOOP_INTERVAL = 3  # 工具链内部请求间隔（秒），远小于正常间隔


def _wait_for_rate_limit(channel: str, tool_loop: bool = False):
    """在发请求前等待，确保不超过渠道的请求频率限制

    每个渠道独立计时。同渠道多线程并发时，先到的占位，后到的排队。
    不同渠道互不影响。

    Args:
        channel: 渠道名
        tool_loop: 是否为工具链内部的后续请求（用更短间隔）
    """
    config = l2.load_config()
    rate_config = config.get("rate_limit", {})

    # 工具链内部用短间隔，正常对话用配置间隔
    if tool_loop:
        interval = TOOL_LOOP_INTERVAL
    else:
        interval = rate_config.get(channel, rate_config.get("default", 0))
    if interval <= 0:
        return

    wait = 0
    with _rate_lock:
        now = time.time()
        last = _last_request_time.get(channel, 0)
        wait = last + interval - now
        if wait > 0:
            # 占位：告诉后续线程"这个时间点已被预约"
            _last_request_time[channel] = last + interval
            print(f"[LLM] 限流等待: {channel} {wait:.1f}s")
        else:
            # 无需等待，直接记录当前时间
            _last_request_time[channel] = now

    # 在锁外 sleep（不阻塞其他渠道的请求）
    if wait > 0:
        time.sleep(wait)


def call(
    messages: List[Dict],
    channel: Optional[str] = None,
    model: Optional[str] = None,
    tools: Optional[List[Dict]] = None,
    **kwargs
) -> str:
    """
    调用 LLM API (单次调用)

    Args:
        messages: 消息列表 [{"role": "system/user/assistant", "content": "..."}]
        channel: 渠道名称 (None 则使用默认)
        model: 模型名称 (None 则使用渠道默认)
        tools: 工具定义列表 (Anthropic 格式)
        **kwargs: 额外参数 (temperature, max_tokens 等)

    Returns:
        str: assistant 的回复文本
    """
    result = call_with_tools(messages, channel, model, tools, **kwargs)
    return result.get("text", "")


def call_with_tools(
    messages: List[Dict],
    channel: Optional[str] = None,
    model: Optional[str] = None,
    tools: Optional[List[Dict]] = None,
    **kwargs
) -> Dict:
    """
    调用 LLM API (返回详细信息，包括 tool_use)

    Args:
        messages: 消息列表
        channel: 渠道名称
        model: 模型名称
        tools: 工具定义列表
        **kwargs: 额外参数

    Returns:
        Dict: {
            "text": 文本内容,
            "has_tool_use": bool,
            "tool_uses": [...],
            "content_blocks": [...],
            "stop_reason": str
        }
    """
    # 0. 提取内部标记 (不传给 provider)
    tool_loop = kwargs.pop("_tool_loop", False)

    # 1. 确定渠道
    if channel is None:
        channel = l2.get_default_channel()

    # 2. 获取渠道配置
    channel_config = l2.get_channel_config(channel)

    # 3. 确定模型和参数
    model_name, model_config = l2.get_model_config(channel_config, model)

    # 打印实际使用的渠道和模型
    tool_info = f", tools={len(tools)}" if tools else ""
    print(f"[LLM] 调用: channel={channel}, model={model_name}{tool_info}")

    # 合并参数 (kwargs > model_config > 默认值)
    temperature = kwargs.get("temperature", model_config.get("temperature", 0.8))
    max_tokens = kwargs.get("max_tokens", model_config.get("max_tokens", 500))

    # 4. 获取适配器
    provider_name = channel_config.get("provider", "openai")
    provider = get_provider(provider_name)

    # 5. 构建请求
    url, headers, payload = provider.build_request(
        messages=messages,
        model=model_name,
        base_url=channel_config.get("base_url", ""),
        api_key=channel_config.get("api_key", ""),
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        **kwargs
    )

    # 6. 限流等待 (工具链内部用短间隔)
    _wait_for_rate_limit(channel, tool_loop=tool_loop)

    # 7. 发送请求
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()

        # 7. 解析响应
        response_data = l2.parse_json_response(response.text)
        return provider.parse_response_with_tools(response_data)

    except requests.exceptions.Timeout:
        raise TimeoutError(f"LLM请求超时: {url}")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"LLM请求失败: {e}")


def get_available_channels() -> list:
    """获取所有可用渠道名称"""
    config = l2.load_config()
    return list(config.get("channels", {}).keys())


def get_channel_models(channel: str) -> list:
    """获取渠道下可用的模型列表"""
    channel_config = l2.get_channel_config(channel)
    models = channel_config.get("models", {})
    return [k for k in models.keys() if k != "default"]
