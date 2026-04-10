# ============================================
# core/drive/drive.py - 驱动系统总控层
# 职责: 配置持有、接口定义、任务分发
# ============================================

import core.drive.drive_l1 as l1
from env.map import MAP_WIDTH, MAP_HEIGHT, THRESHOLD_CONTACT, THRESHOLD_LEAVE

# ========== 配置区 ==========
STEP_SIZE = 1.0              # 每次移动步长
RECOVERY_INTERVAL = 50       # 主动值恢复间隔 (tick)

# ========== 状态区 ==========
_tick_counter = 0            # 内部 tick 计数器


def reset_counter():
    """重置内部 tick 计数器 (世界切换时调用)"""
    global _tick_counter
    _tick_counter = 0


# ========== 接口区 ==========
def update_all(npcs):
    """
    更新所有NPC的驱动状态
    包括: 物理移动 + 空间感知 + 状态切换 + 主动值恢复
    """
    global _tick_counter
    _tick_counter += 1

    # 每 RECOVERY_INTERVAL tick 恢复一次主动值
    should_recover = (_tick_counter % RECOVERY_INTERVAL == 0)

    return l1.update_drive_logic(
        npcs,
        step_size=STEP_SIZE,
        map_width=MAP_WIDTH,
        map_height=MAP_HEIGHT,
        th_contact=THRESHOLD_CONTACT,
        th_leave=THRESHOLD_LEAVE,
        should_recover=should_recover
    )
