# ============================================
# tools/form_l1.py - 表单系统业务层 (L1)
# 职责: ask_human 工具实现 (文本对话式)
# ============================================

from typing import Dict
from tools import form as form_module


def ask_human(
    question: str,
    context: str = "",
    from_npc: str = "系统",
    timeout: int = 300
) -> Dict:
    """
    向人类提问并等待文字回复 (阻塞式)

    这是 AI 获取人类意向的核心工具。
    调用后会阻塞等待人类输入文字回复。

    Args:
        question: 要问的问题
        context: 背景说明 (可选)
        from_npc: 发起者 NPC 名称
        timeout: 超时时间 (秒)，默认 5 分钟

    Returns:
        人类的文字回复，或超时/错误信息
    """
    # 创建一个简单的文本输入表单
    form = form_module.create_form(
        title=question[:50] + ("..." if len(question) > 50 else ""),
        description=context or question,
        fields=[{
            "name": "answer",
            "label": "你的回复",
            "type": "textarea",
            "required": True,
            "placeholder": "请输入你的回答...",
        }],
        from_npc=from_npc,
        timeout=timeout
    )

    form_id = form["id"]

    # 阻塞等待响应
    response = form_module.get_response(form_id, wait=True, timeout=timeout)

    if response is None:
        status = form_module._form_status.get(form_id, "unknown")
        if status == "expired":
            return {"status": "timeout", "message": "用户未在规定时间内回复"}
        elif status == "cancelled":
            return {"status": "cancelled", "message": "用户取消了回复"}
        else:
            return {"status": "timeout", "message": f"等待回复超时 ({timeout}秒)"}

    # 返回用户的文字回复
    answer = response.get("response", {}).get("answer", "")
    return {
        "status": "answered",
        "answer": answer,
        "submitted_at": response.get("submitted_at")
    }


# ========== 工具 Handler ==========

def _tool_ask_human(input_obj: dict, npc, context) -> str:
    """
    ask_human 工具的 Handler

    AI 调用示例:
    {
        "question": "我准备写一个剧本，你希望是温馨风格还是剧情向？",
        "context": "这是为深夜陪伴模式准备的",
        "timeout": 300
    }
    """
    question = input_obj.get("question", "")
    context_info = input_obj.get("context", "")
    timeout = input_obj.get("timeout", 300)

    from_npc = npc.name if npc else "系统"

    result = ask_human(
        question=question,
        context=context_info,
        from_npc=from_npc,
        timeout=timeout
    )

    if result.get("status") == "answered":
        answer = result.get("answer", "")
        return f"用户的回复: {answer}"
    elif result.get("status") == "timeout":
        return "等待用户回复超时"
    elif result.get("status") == "cancelled":
        return "用户取消了回复"
    else:
        return f"获取回复失败: {result.get('message', '未知错误')}"


# 保留兼容旧名称
def _tool_send_form(input_obj: dict, npc, context) -> str:
    """send_form 的兼容层，实际调用 ask_human"""
    question = input_obj.get("title", "请回答")
    context_info = input_obj.get("description", "")
    timeout = input_obj.get("timeout", 300)
    return _tool_ask_human({
        "question": question,
        "context": context_info,
        "timeout": timeout
    }, npc, context)


def _tool_ask_choice(input_obj: dict, npc, context) -> str:
    """ask_choice 的兼容层，实际调用 ask_human（在问题中包含选项）"""
    question = input_obj.get("question", "请选择")
    options = input_obj.get("options", [])
    timeout = input_obj.get("timeout", 300)

    # 把选项加入问题
    if options:
        options_text = " / ".join(str(o) for o in options)
        full_question = f"{question}\n\n可选: {options_text}"
    else:
        full_question = question

    return _tool_ask_human({
        "question": full_question,
        "context": "",
        "timeout": timeout
    }, npc, context)


def _tool_ask_confirm(input_obj: dict, npc, context) -> str:
    """ask_confirm 的兼容层，实际调用 ask_human"""
    message = input_obj.get("message", "确认?")
    timeout = input_obj.get("timeout", 300)

    return _tool_ask_human({
        "question": f"{message}\n\n请回复「确认」或「取消」",
        "context": "",
        "timeout": timeout
    }, npc, context)
