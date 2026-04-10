# ============================================
# core/social/social_l2.py - 交互原子层
# 职责: 纯逻辑判断, 无状态, 纯计算
# ============================================


# ========== 距离与主动值判定 ==========

def is_contact(dist, limit):
    """判断两点是否在接触范围内"""
    return dist <= limit


def compare_initiative(npc_a, npc_b):
    """
    比较主动值, 返回胜出者
    平局时 A 有惯性优势
    """
    if npc_a.initiative >= npc_b.initiative:
        return npc_a
    return npc_b


def should_continue_talking(speaker_initiative):
    """判断发言者是否还有能量继续说话"""
    return speaker_initiative >= 0


# ========== 记忆格式化 (纯字符串转换) ==========

def format_conversation_record(timestamp, other_name, content, is_self):
    """格式化单条对话记录为记忆文本

    Args:
        timestamp: 时间戳字符串
        other_name: 对话对象名称
        content: 对话内容
        is_self: True=自己说的, False=对方说的

    Returns:
        str: 格式化后的记忆文本
    """
    if is_self:
        return f"[{timestamp}] 我对{other_name}说: {content}"
    else:
        return f"[{timestamp}] {other_name}对我说: {content}"


def format_location_record(timestamp, location_name, content, is_self):
    """格式化地点对话记录

    Args:
        timestamp: 时间戳字符串
        location_name: 地点名称
        content: 对话内容
        is_self: True=NPC回复, False=地点发言

    Returns:
        str: 格式化后的记忆文本
    """
    if is_self:
        return f"[{timestamp}] 在{location_name}: {content}"
    else:
        return f"[{timestamp}] 到达{location_name}: {content}"


def format_timer_record(timestamp, description, content, is_self):
    """格式化定时器对话记录

    Args:
        timestamp: 时间戳字符串
        description: 定时器描述
        content: 对话内容
        is_self: True=NPC回复, False=提醒消息

    Returns:
        str: 格式化后的记忆文本
    """
    if is_self:
        return f"[{timestamp}] 定时提醒({description[:20]}...): {content}"
    else:
        return f"[{timestamp}] 收到定时提醒: {content}"


def buffer_to_history(buffer, timestamp, other_name, formatter):
    """将 ram_buffer 批量转换为 hdd_history 记录

    Args:
        buffer: ram_buffer 列表 [{"role": "assistant"|"user", "content": "..."}]
        timestamp: 时间戳字符串
        other_name: 对话对象名称/地点名称/定时器描述
        formatter: 格式化函数 (timestamp, other_name, content, is_self) -> str

    Returns:
        list[str]: 格式化后的记忆记录列表
    """
    records = []
    for msg in buffer:
        is_self = (msg.get('role') == 'assistant')
        record = formatter(timestamp, other_name, msg.get('content', ''), is_self)
        records.append(record)
    return records


# ========== 历史记忆筛选 (纯计算) ==========

def select_relevant_memories(history, listener_name, max_relevant=5, max_total=5):
    """从历史记忆中选择与对话对象相关的记录

    Args:
        history: 完整历史记忆列表
        listener_name: 对话对象名称
        max_relevant: 最多取多少条相关记忆
        max_total: 最终返回的总条数上限

    Returns:
        list[str]: 筛选后的记忆列表
    """
    # 先标准化 (兼容 dict 格式旧数据)
    normalized = []
    for item in history:
        if isinstance(item, str):
            normalized.append(item)
        elif isinstance(item, dict):
            role = item.get('role', 'unknown')
            content = item.get('content', '')
            normalized.append(f"[{role}] {content}")

    # 优先选择与当前对话对象相关的记忆
    relevant = [r for r in normalized if listener_name in r]
    if len(relevant) >= max_relevant:
        return relevant[-max_total:]
    elif relevant:
        other = [r for r in normalized if listener_name not in r]
        return relevant + other[-(max_total - len(relevant)):]
    else:
        return normalized[-max_total:]
