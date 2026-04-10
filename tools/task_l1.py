# ============================================
# tools/task_l1.py - 任务系统业务层 (L1)
# 职责: 工具处理函数、任务执行逻辑
# ============================================

from tools import task as task_module


def _tool_add_task(input_obj: dict, npc, context) -> str:
    """
    添加任务工具

    NPC 调用此工具给他人添加任务提醒

    Args:
        input_obj: {"target": "Alice", "hint": "去看文件", "tool_hint": "read_file: path=xxx"}
        npc: 调用者
        context: 上下文

    Returns:
        str: 执行结果
    """
    target_name = input_obj.get("target", "")
    hint = input_obj.get("hint", "")

    if not target_name or not hint:
        return "错误: 缺少 target 或 hint 参数"

    # 规范化名称: 首字母大写
    target_name = target_name.capitalize()

    # 创建任务并添加到全局池
    task = task_module.create_task(
        hint=hint,
        source=npc.name,
        tool_hint=input_obj.get("tool_hint"),
    )
    task_module.add_task_to_pool(target_name, task)

    print(f"[Task] {npc.name} -> {target_name}: {hint}")
    return f"已为 {target_name} 添加任务: {hint}"


def _tool_complete_task(input_obj: dict, npc, context) -> str:
    """
    完成任务工具

    NPC 完成任务后调用此工具标记完成

    Args:
        input_obj: {"hint": "文件"}  # 模糊匹配
        npc: 调用者 (谁在完成任务)
        context: 上下文

    Returns:
        str: 执行结果
    """
    hint = input_obj.get("hint", "")

    if not hint:
        return "错误: 缺少 hint 参数"

    # 从全局池中完成任务
    count = task_module.complete_task_in_pool(npc.name, hint)

    if count > 0:
        print(f"[Task] {npc.name} 完成 {count} 个任务: {hint}")
        return f"已完成 {count} 个任务"
    else:
        return "未找到匹配的任务"
