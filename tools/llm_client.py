# ============================================
# tools/llm_client.py - LLM工具总控层
# 职责: 配置持有、接口定义
# ============================================

from typing import List, Dict, Optional, Any
from tools import llm_l1, llm_l2

# === Mock模式 ===
USE_MOCK = False

# === 当前渠道/模型 (可通过代码切换) ===
_current_channel = None
_current_model = None


# === 接口 ===
def init():
    """初始化LLM，加载配置"""
    config = llm_l2.load_config()
    routing = config.get("routing", {})

    global _current_channel, _current_model
    _current_channel = routing.get("default_channel", "")
    _current_model = routing.get("default_model")

    print(f"[LLM] 默认渠道: {_current_channel}, Mock: {USE_MOCK}")


def chat(
    messages: List[Dict],
    channel: Optional[str] = None,
    model: Optional[str] = None,
    tools: Optional[List[Dict]] = None,
    **kwargs
) -> str:
    """
    对话接口 (单次调用，不处理工具链)

    Args:
        messages: [{"role": "system/user/assistant", "content": "..."}]
        channel: 渠道名称 (None 则使用当前/默认渠道)
        model: 模型名称 (None 则使用当前/默认模型)
        tools: 工具定义列表 (Anthropic 格式)
        **kwargs: 额外参数 (temperature, max_tokens 等)

    Returns:
        str: assistant 的回复文本
    """
    if USE_MOCK:
        return _mock_generate()

    # 使用传入值或当前设置
    use_channel = channel or _current_channel
    use_model = model or _current_model

    try:
        return llm_l1.call(messages, channel=use_channel, model=use_model, tools=tools, **kwargs)
    except Exception as e:
        return f"[LLM调用失败: {e}]"


def chat_with_tools(
    messages: List[Dict],
    channel: Optional[str] = None,
    model: Optional[str] = None,
    tools: Optional[List[Dict]] = None,
    tool_executor: callable = None,
    max_tool_loops: int = 10,
    cancel_event=None,
    **kwargs
) -> Dict:
    """
    带工具链的对话接口 (循环调用直到任务完成)

    Args:
        messages: 消息列表
        channel: 渠道名称
        model: 模型名称
        tools: 工具定义列表
        tool_executor: 工具执行器函数 (tool_uses, npc, context) -> results
        max_tool_loops: 最大工具循环次数
        **kwargs: 额外参数

    Returns:
        Dict: {
            "text": 最终文本回复,
            "tool_calls": 所有工具调用记录,
            "raw_responses": 所有原始响应
        }
    """
    if USE_MOCK:
        return {"text": _mock_generate(), "tool_calls": [], "raw_responses": []}

    use_channel = channel or _current_channel
    use_model = model or _current_model

    all_tool_calls = []
    all_responses = []
    current_messages = list(messages)  # 复制消息列表

    loop_count = 0
    consecutive_failures = 0  # 连续失败计数
    MAX_CONSECUTIVE_FAILURES = 3  # 连续失败 3 次则提前中断

    while loop_count < max_tool_loops:
        # 检查取消标志
        if cancel_event and cancel_event.is_set():
            print(f"[LLM] 🛑 工具链被取消，停止循环 (第 {loop_count} 轮)")
            return {
                "text": "[任务已停止]",
                "tool_calls": all_tool_calls,
                "raw_responses": all_responses,
            }

        loop_count += 1

        # 调用 LLM (工具链内部用短间隔限流)
        try:
            result = llm_l1.call_with_tools(
                messages=current_messages,
                channel=use_channel,
                model=use_model,
                tools=tools,
                _tool_loop=(loop_count > 1),  # 第2轮起标记为工具链内部
                **kwargs
            )
        except Exception as e:
            # LLM 调用失败，返回错误信息
            print(f"[LLM] 调用失败: {e}")
            return {
                "text": f"[系统繁忙，请稍后重试]",
                "tool_calls": all_tool_calls,
                "raw_responses": all_responses,
                "error": str(e)
            }

        all_responses.append(result)

        # 检查是否有 tool_use
        if not result.get("has_tool_use"):
            # 没有工具调用，返回最终文本
            return {
                "text": result.get("text", ""),
                "tool_calls": all_tool_calls,
                "raw_responses": all_responses,
            }

        # 有工具调用
        tool_uses = result.get("tool_uses", [])
        all_tool_calls.extend(tool_uses)

        if tool_executor:
            # 执行工具
            tool_results = tool_executor(tool_uses)

            # 检测本轮是否全部失败 (用于连续失败中断)
            all_failed = all(
                any(kw in str(tr.get("content", "")) for kw in ("错误:", "[失败", "未知工具:"))
                for tr in tool_results
            ) if tool_results else False

            if all_failed:
                consecutive_failures += 1
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    print(f"[LLM] ⚠️ 连续 {consecutive_failures} 轮工具调用全部失败，提前中断")
                    # 注入提示让 LLM 停止尝试，直接回复
                    current_messages.append({
                        "role": "assistant",
                        "content": result.get("content_blocks", [])
                    })
                    current_messages.append({
                        "role": "user",
                        "content": tool_results + [{
                            "type": "tool_result",
                            "tool_use_id": tool_results[-1].get("tool_use_id", ""),
                            "content": "[系统提示] 工具已连续多次失败，请停止调用工具，直接用文字回复用户。"
                        }]
                    })
                    # 最后一次调用 LLM 让它生成文字回复
                    try:
                        final_result = llm_l1.call_with_tools(
                            messages=current_messages,
                            channel=use_channel,
                            model=use_model,
                            tools=[],  # 不给工具，强制文字回复
                            **kwargs
                        )
                        return {
                            "text": final_result.get("text", "[工具调用失败，无法完成任务]"),
                            "tool_calls": all_tool_calls,
                            "raw_responses": all_responses,
                        }
                    except Exception:
                        return {
                            "text": "[工具连续失败，系统中断]",
                            "tool_calls": all_tool_calls,
                            "raw_responses": all_responses,
                            "error": f"连续 {consecutive_failures} 轮工具失败"
                        }
            else:
                consecutive_failures = 0  # 有成功则重置计数

            # 将 assistant 消息和 tool_result 添加到消息列表
            current_messages.append({
                "role": "assistant",
                "content": result.get("content_blocks", [])
            })
            current_messages.append({
                "role": "user",
                "content": tool_results
            })

            print(f"[LLM] 工具链循环 {loop_count}: 执行了 {len(tool_uses)} 个工具")
        else:
            # 没有执行器，直接返回
            return {
                "text": result.get("text", ""),
                "tool_calls": all_tool_calls,
                "raw_responses": all_responses,
                "error": "没有提供 tool_executor"
            }

    # 达到最大循环次数
    return {
        "text": "",
        "tool_calls": all_tool_calls,
        "raw_responses": all_responses,
        "error": f"达到最大工具循环次数 {max_tool_loops}"
    }


def set_channel(channel: str):
    """切换当前渠道"""
    global _current_channel
    _current_channel = channel
    print(f"[LLM] 切换渠道: {channel}")


def set_model(model: str):
    """切换当前模型"""
    global _current_model
    _current_model = model
    print(f"[LLM] 切换模型: {model}")


def list_channels() -> list:
    """获取所有可用渠道"""
    return llm_l1.get_available_channels()


def list_models(channel: str = None) -> list:
    """获取渠道下的模型列表"""
    use_channel = channel or _current_channel
    return llm_l1.get_channel_models(use_channel)


def reload_config():
    """重新加载配置文件"""
    llm_l2.reload_config()
    init()


def _mock_generate() -> str:
    """Mock模式"""
    import random
    responses = [
        "你好啊，今天天气不错。",
        "哦？有什么事吗？",
        "嗯，让我想想。",
        "这样啊，真有趣。"
    ]
    return random.choice(responses)
