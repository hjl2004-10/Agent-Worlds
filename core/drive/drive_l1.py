# ============================================
# core/drive/drive_l1.py - 驱动业务层
# 职责: 个体作用域, 流程组装, 状态流转控制
# ============================================

import core.drive.drive_l2 as l2
import core.social.social as social
from body.npc import WalkMode


def update_drive_logic(npcs, step_size, map_width, map_height, th_contact, th_leave,
                       should_recover=False):
    """
    核心驱动逻辑 - 状态流转控制器
    协调 移动 与 社交 的切换
    """
    # === 阶段0: 过滤禁用 NPC ===
    active_npcs = [npc for npc in npcs if npc.enabled]

    # === 阶段1: 主动值恢复 (仅限闲逛状态) ===
    if should_recover:
        for npc in active_npcs:
            if not npc.is_talking and npc.initiative < npc.max_initiative:
                npc.initiative += 1
                print(f"💚 {npc.name} 主动值恢复: {npc.initiative-1} -> {npc.initiative}")

    # === 阶段2: 物理移动 (只针对没在说话的NPC) ===
    for npc in active_npcs:
        if not npc.is_talking:
            # 上帝模式: 玩家控制移动 (持续移动直到方向被清除)
            if npc.god_controlled and npc.god_move_direction:
                # 上帝模式使用更大的步长 (3倍速度)
                god_step = step_size * 10
                npc.x, npc.y = l2.god_mode_step(
                    npc.x, npc.y,
                    npc.god_move_direction,
                    god_step,
                    map_width, map_height
                )
                # 不消费方向，保持持续移动
                continue

            # === to_target 模式移动 (goto 工具设置) ===
            if npc.walk_mode == WalkMode.TO_TARGET and npc.walk_target is not None:
                target_x, target_y = npc.walk_target
                npc.x, npc.y, arrived = l2.move_toward_target(
                    npc.x, npc.y, target_x, target_y, step_size
                )
                if arrived:
                    location_name = getattr(npc, 'walk_target_name', None)
                    print(f"✅ {npc.name} 已到达目标坐标: ({target_x:.1f}, {target_y:.1f})")
                    # 注意: 不在这里设置 idle，等 NPC 调用 arrived_at 工具后再设置
                    # 清除坐标目标，但保留 walk_target_name 用于对话
                    npc.walk_target = None
                    npc.walk_mode_tick = 0

                    # 触发地点碰撞对话
                    if location_name:
                        _trigger_location_encounter(npc, location_name)
                continue  # 移动中或到达后都跳过自动漫游

            # === 自动漫游模式 (三态循环: idle -> random -> linear -> idle) ===
            # 更新行走模式计数
            npc.walk_mode_tick += 1

            # 检查是否需要切换模式 (使用NPC自身配置)
            # 三态循环: idle -> random -> linear -> idle
            if npc.walk_mode == WalkMode.IDLE and npc.walk_mode_tick >= npc.walk_idle_duration:
                # idle -> random: 静默结束，开始随机漫步
                npc.walk_mode = WalkMode.RANDOM
                npc.walk_mode_tick = 0
                print(f"[Walk] {npc.name} idle -> random")
            elif npc.walk_mode == WalkMode.RANDOM and npc.walk_mode_tick >= npc.walk_random_duration:
                # random -> linear: 随机漫步结束，开始直线行走
                npc.walk_mode = WalkMode.LINEAR
                npc.walk_mode_tick = 0
                npc.walk_direction = l2.generate_direction()
                print(f"[Walk] {npc.name} random -> linear")
            elif npc.walk_mode == WalkMode.LINEAR and npc.walk_mode_tick >= npc.walk_linear_duration:
                # linear -> idle: 直线行走结束，进入静默
                npc.walk_mode = WalkMode.IDLE
                npc.walk_mode_tick = 0
                print(f"[Walk] {npc.name} linear -> idle")

            # 根据模式执行移动 (idle 模式不移动)
            if npc.walk_mode == WalkMode.RANDOM:
                npc.x, npc.y = l2.random_step(
                    npc.x, npc.y,
                    step_size,
                    map_width, map_height
                )
            elif npc.walk_mode == WalkMode.LINEAR:
                npc.x, npc.y, npc.walk_direction = l2.linear_step(
                    npc.x, npc.y,
                    npc.walk_direction,
                    step_size,
                    map_width, map_height
                )
            # idle 模式: 不移动，原地静止

    # === 阶段3: 空间感知与状态切换 (仅活跃 NPC 之间) ===
    # 两两遍历 O(N^2) MVP写法
    for i in range(len(active_npcs)):
        for j in range(i + 1, len(active_npcs)):
            npc_a = active_npcs[i]
            npc_b = active_npcs[j]

            # 1. 计算距离
            dist = l2.calc_distance(npc_a.x, npc_a.y, npc_b.x, npc_b.y)

            # 2. 检查 A 是否 ban 了 B
            is_banned = (npc_a.ban_target_uuid == npc_b.name)

            # 3. 原子层迟滞判定
            should_talk, should_clear = l2.check_hysteresis_state(
                dist,
                npc_b.name if is_banned else None,
                th_contact,
                th_leave
            )

            # === 分支A: 触发对话 (进入LLM流) ===
            # 检查是否有一方禁用了碰撞
            a_no_collision = npc_a.memory.get('no_collision', False)
            b_no_collision = npc_b.memory.get('no_collision', False)

            if should_talk and not npc_a.is_talking and not npc_b.is_talking and not a_no_collision and not b_no_collision:
                # 创建异步对话任务 (非阻塞，NPC 冻结由 create_task 处理)
                print(f"⚡ 触发接触: {npc_a.name} <-> {npc_b.name} (距离: {dist:.2f})")
                task = social.start_npc_conversation(npc_a, npc_b)
                if not task:
                    # 达到并发上限或 NPC 已忙，跳过
                    print(f"⏳ 对话队列已满，跳过: {npc_a.name} <-> {npc_b.name}")
                # 注: ban_target_uuid 在对话任务完成时设置 (见 social_l1._on_task_done)

            # === 分支B: 解除禁止 (恢复常态) ===
            elif should_clear:
                npc_a.ban_target_uuid = None
                npc_b.ban_target_uuid = None
                print(f"🔓 解锁: {npc_a.name} 与 {npc_b.name} 已远离, 可再次互动")


def _trigger_location_encounter(npc, location_name: str):
    """
    触发地点碰撞对话 (异步版)

    Args:
        npc: 到达地点的 NPC
        location_name: 地点名称
    """
    from env import map as map_module

    # 获取地点信息
    locations = map_module.get_all_locations()
    if location_name not in locations:
        return

    print(f"🏛️ [地点碰撞] {npc.name} 到达 {location_name}")

    # 创建异步对话任务 (非阻塞，NPC 冻结由 create_task 处理)
    task = social.start_location_conversation(npc, location_name)
    if not task:
        print(f"⏳ 对话队列已满，跳过地点对话: {npc.name} @ {location_name}")
