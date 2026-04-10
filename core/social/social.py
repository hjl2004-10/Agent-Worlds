# ============================================
# core/social/social.py - 交互系统总控层
# 职责: 配置持有、接口定义
# ============================================

import core.social.social_l1 as l1
from core.social.conversation_task import (
    ConvType, create_task, is_npc_busy, is_at_capacity,
)

# ========== 配置区 ==========
CONTACT_THRESHOLD = 2.0  # 接触距离 (用于参考, 实际由drive判定)


# ========== 旧接口 (保留兼容) ==========
def run(npc_a, npc_b):
    """
    运行两个NPC之间的对话交互 (阻塞版，保留兼容)
    """
    return l1.run_conversation(npc_a, npc_b)


def run_location_encounter(npc, location_name: str):
    """
    运行NPC与地点的碰撞对话 (阻塞版，保留兼容)
    """
    return l1.run_location_conversation(npc, location_name)


# ========== 新接口 (异步 tick 驱动) ==========

def tick_all():
    """每个主循环 tick 调用，推进所有活跃对话 (非阻塞)"""
    l1.tick_all()


def start_npc_conversation(npc_a, npc_b):
    """创建 NPC-NPC 对话任务 (非阻塞)

    Returns:
        ConversationTask or None (达到上限或 NPC 正忙)
    """
    if is_at_capacity():
        return None
    if is_npc_busy(npc_a.name) or is_npc_busy(npc_b.name):
        return None
    return create_task(ConvType.NPC_NPC, npc_a, npc_b)


def start_location_conversation(npc, location_name):
    """创建地点对话任务 (非阻塞)"""
    if is_at_capacity():
        return None
    if is_npc_busy(npc.name):
        return None
    return create_task(ConvType.LOCATION, npc, location_name=location_name)


def start_timer_conversation(npc, description):
    """创建定时器对话任务 (非阻塞)"""
    if is_at_capacity():
        return None
    if is_npc_busy(npc.name):
        return None
    return create_task(ConvType.TIMER, npc, timer_desc=description)


def start_wechat_conversation(npc, trigger_text: str):
    """创建微信对话任务 (非阻塞)

    Args:
        npc: 绑定微信的 NPC
        trigger_text: 微信用户发来的消息
    """
    if is_at_capacity():
        return None
    if is_npc_busy(npc.name):
        return None
    return create_task(ConvType.WECHAT, npc, wechat_trigger=trigger_text)


def can_start_conversation():
    """是否还能开启新对话"""
    return not is_at_capacity()
