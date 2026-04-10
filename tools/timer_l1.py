# ============================================
# tools/timer_l1.py - 定时器业务层 (L1)
# 职责: 定时器检查、触发对话
# ============================================

from typing import Dict, List, Optional, TYPE_CHECKING

from tools import timer as timer_module

if TYPE_CHECKING:
    from body.npc import Agent


def check_timers(current_tick: int, npcs: List["Agent"]) -> List[Dict]:
    """
    检查是否有定时器需要触发

    Args:
        current_tick: 当前 tick
        npcs: NPC 列表

    Returns:
        List[Dict]: 触发结果列表
    """
    results = []
    timers = timer_module.get_all_timers()

    for t in timers:
        if not t.get("enabled", True):
            continue

        target = t.get("target", "")
        interval = t.get("interval_ticks", 0)
        last_tick = t.get("last_trigger_tick", 0)

        # 检查是否到达触发时间
        if current_tick - last_tick >= interval:
            # 找到目标 NPC
            target_npc = None
            for npc in npcs:
                if npc.name.lower() == target.lower():
                    target_npc = npc
                    break

            if target_npc:
                # 检查 NPC 是否启用
                if not target_npc.enabled:
                    continue

                # 触发对话
                result = trigger_timer_conversation(t, target_npc, current_tick)
                results.append(result)

                # 更新触发次数
                timer_module.increment_trigger(t["id"], current_tick)

    return results


def trigger_timer_conversation(timer: Dict, npc: "Agent", current_tick: int) -> Dict:
    """
    触发定时器对话

    系统用定时器的 description 向 NPC 发起主动对话，
    消耗 NPC 的一次主动值。

    Args:
        timer: 定时器对象
        npc: 目标 NPC
        current_tick: 当前 tick

    Returns:
        Dict: 触发结果
    """
    description = timer.get("description", "")

    # 检查 NPC 主动值
    if npc.initiative < 0:
        return {
            "status": "skipped",
            "reason": "主动值不足",
            "timer": timer["name"],
            "npc": npc.name
        }

    # 检查 NPC 是否正在对话
    if npc.is_talking:
        return {
            "status": "skipped",
            "reason": "NPC 正在对话中",
            "timer": timer["name"],
            "npc": npc.name
        }

    # 创建异步对话任务 (非阻塞，NPC 冻结由 create_task 处理)
    from core.social.social import start_timer_conversation
    task = start_timer_conversation(npc, description)

    if task:
        return {
            "status": "triggered",
            "timer": timer["name"],
            "npc": npc.name,
            "description": description,
            "task_id": task.id
        }
    else:
        return {
            "status": "skipped",
            "reason": "对话队列已满",
            "timer": timer["name"],
            "npc": npc.name
        }


# ========== 工具处理函数 ==========

def _tool_create_timer(input_obj: dict, npc, context) -> str:
    """
    创建定时器 (NPC 工具)

    参数:
        name: 定时器名称
        description: 触发时的提示内容
        interval_ticks: 触发间隔 (tick)
        max_triggers: 最大触发次数 (-1 无限)

    注意: 目标 NPC 就是调用者自己
    """
    name = input_obj.get("name", "")
    description = input_obj.get("description", "")
    interval_ticks = input_obj.get("interval_ticks", 120)  # 默认 120 tick = 1小时
    max_triggers = input_obj.get("max_triggers", -1)

    if not name or not description:
        return "错误: 缺少 name 或 description 参数"

    # 创建定时器 (目标是自己)
    timer = timer_module.create_timer(
        name=name,
        description=description,
        target=npc.name,
        interval_ticks=interval_ticks,
        max_triggers=max_triggers
    )
    timer_module.add_timer(timer)

    # 计算游戏内时间显示
    hours = interval_ticks / 120  # 120 tick = 1 游戏小时

    return f"定时器 '{name}' 已创建: 每 {hours:.1f} 游戏小时提醒你 '{description}'"


def _tool_remove_timer(input_obj: dict, npc, context) -> str:
    """
    移除定时器 (NPC 工具)

    参数:
        name: 定时器名称
    """
    name = input_obj.get("name", "")

    if not name:
        return "错误: 缺少 name 参数"

    # 查找自己的定时器
    timers = timer_module.get_timers_for(npc.name)
    for t in timers:
        if t.get("name") == name:
            timer_module.remove_timer(t["id"])
            return f"定时器 '{name}' 已删除"

    return f"错误: 未找到名为 '{name}' 的定时器"


def _tool_list_timers(input_obj: dict, npc, context) -> str:
    """
    列出自己的定时器 (NPC 工具)
    """
    timers = timer_module.get_timers_for(npc.name)

    if not timers:
        return "你没有设置任何定时器"

    lines = ["你的定时器:"]
    for t in timers:
        status = "启用" if t.get("enabled", True) else "已禁用"
        hours = t.get("interval_ticks", 0) / 120
        max_t = t.get("max_triggers", -1)
        triggered = t.get("triggered_count", 0)

        max_str = f" (剩余 {max_t - triggered} 次)" if max_t > 0 else ""
        lines.append(f"- {t['name']}: 每 {hours:.1f} 小时 | {status}{max_str}")
        lines.append(f"  提示: {t['description']}")

    return "\n".join(lines)
