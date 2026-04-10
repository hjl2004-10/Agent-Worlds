# ============================================
# core/drive/drive_l2.py - 驱动原子层
# 职责: 纯数学计算, 无状态
# ============================================

import math
import random


def random_step(x, y, step_size, max_w, max_h):
    """
    计算随机漫步后的新坐标
    并限制在地图矩形内，检测障碍物碰撞
    碰到障碍物时尝试其他随机方向（最多3次）
    """
    from env import map as map_module

    for _ in range(3):
        dx = random.uniform(-step_size, step_size)
        dy = random.uniform(-step_size, step_size)

        new_x = max(0, min(max_w, x + dx))
        new_y = max(0, min(max_h, y + dy))

        if not map_module.is_blocked(new_x, new_y):
            return new_x, new_y

    return x, y  # 3次都被阻挡，保持原位


def generate_direction():
    """
    生成随机方向角度 (弧度)
    返回: 0 ~ 2π
    """
    return random.uniform(0, 2 * math.pi)


def linear_step(x, y, direction, step_size, max_w, max_h):
    """
    沿固定方向直线行走

    Args:
        x, y: 当前坐标
        direction: 行走方向 (弧度)
        step_size: 步长
        max_w, max_h: 地图边界

    Returns:
        (new_x, new_y, new_direction)
        如果撞墙则反弹，返回新方向
    """
    dx = math.cos(direction) * step_size
    dy = math.sin(direction) * step_size

    new_x = x + dx
    new_y = y + dy
    new_direction = direction

    # 撞墙反弹
    if new_x <= 0 or new_x >= max_w:
        new_direction = math.pi - direction  # 水平反弹
        new_x = max(0, min(max_w, new_x))

    if new_y <= 0 or new_y >= max_h:
        new_direction = -direction  # 垂直反弹
        new_y = max(0, min(max_h, new_y))

    # 规范化方向到 [0, 2π]
    new_direction = new_direction % (2 * math.pi)

    # 障碍物碰撞检测
    from env import map as map_module
    if map_module.is_blocked(new_x, new_y):
        # 撞到障碍物也反弹
        new_direction = (direction + math.pi / 2) % (2 * math.pi)
        return x, y, new_direction

    return new_x, new_y, new_direction


def calc_distance(x1, y1, x2, y2):
    """欧几里得距离计算"""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def check_hysteresis_state(dist, current_ban_target, th_contact, th_leave):
    """
    迟滞状态机判定

    Args:
        dist: 当前距离
        current_ban_target: 当前被ban的目标 (None表示未ban)
        th_contact: 触发对话的距离阈值
        th_leave: 解除禁止的距离阈值

    Returns:
        (should_trigger_talk, should_clear_ban)
    """
    # 1. 判定是否应该触发对话: 距离够近 且 没被ban
    should_talk = (dist <= th_contact) and (current_ban_target is None)

    # 2. 判定是否应该解除禁止: 距离够远 且 正被ban
    should_clear = (dist >= th_leave) and (current_ban_target is not None)

    return should_talk, should_clear


def move_toward_target(x, y, target_x, target_y, step_size):
    """
    从当前位置向目标点移动，支持避障绕行

    Args:
        x, y: 当前坐标
        target_x, target_y: 目标坐标
        step_size: 步长

    Returns:
        (new_x, new_y, arrived)
        arrived: 是否已到达目标 (True 则 new_x/y 等于目标坐标)
    """
    from env import map as map_module
    from env import map_l2

    dx = target_x - x
    dy = target_y - y
    dist = math.sqrt(dx ** 2 + dy ** 2)

    # 已到达 (距离小于一步)
    if dist <= step_size:
        # 检查目标点是否被阻挡
        if map_module.is_blocked(target_x, target_y):
            return x, y, False  # 目标被阻挡，无法到达
        return target_x, target_y, True

    # 沿方向移动一步
    ratio = step_size / dist
    new_x = x + dx * ratio
    new_y = y + dy * ratio

    # 障碍物碰撞检测
    if not map_module.is_blocked(new_x, new_y):
        return new_x, new_y, False

    # === 避障绕行逻辑 ===
    # 尝试多个方向绕行
    obstacles = map_module.get_obstacles()
    blocking = map_l2.find_blocking_obstacle(x, y, new_x, new_y, obstacles)

    if blocking:
        # 获取绕行方向
        detour_dx, detour_dy = map_l2.find_detour_direction(x, y, target_x, target_y, blocking)

        # 归一化绕行方向
        detour_dist = math.sqrt(detour_dx ** 2 + detour_dy ** 2)
        if detour_dist > 0:
            detour_dx /= detour_dist
            detour_dy /= detour_dist

            # 尝试沿绕行方向移动
            detour_x = x + detour_dx * step_size
            detour_y = y + detour_dy * step_size

            if not map_module.is_blocked(detour_x, detour_y):
                return detour_x, detour_y, False

            # 绕行方向也被阻挡，尝试反方向
            detour_x = x - detour_dx * step_size
            detour_y = y - detour_dy * step_size

            if not map_module.is_blocked(detour_x, detour_y):
                return detour_x, detour_y, False

    # 尝试垂直方向绕行 (备选方案)
    perp_dx = -dy / dist  # 垂直于目标方向
    perp_dy = dx / dist

    # 尝试两个垂直方向
    for sign in [1, -1]:
        test_x = x + sign * perp_dx * step_size
        test_y = y + sign * perp_dy * step_size
        if not map_module.is_blocked(test_x, test_y):
            return test_x, test_y, False

    # 所有方向都被阻挡，保持原位
    return x, y, False


def god_mode_step(x, y, direction, step_size, max_w, max_h):
    """
    上帝模式: 按指定方向移动

    Args:
        x, y: 当前坐标
        direction: 移动方向 ('up'|'down'|'left'|'right')
        step_size: 步长
        max_w, max_h: 地图边界

    Returns:
        (new_x, new_y)
    """
    dx, dy = 0, 0

    if direction == 'up':
        dy = -step_size
    elif direction == 'down':
        dy = step_size
    elif direction == 'left':
        dx = -step_size
    elif direction == 'right':
        dx = step_size

    new_x = max(0, min(max_w, x + dx))
    new_y = max(0, min(max_h, y + dy))

    # 障碍物碰撞检测 (上帝模式也可以被阻挡)
    from env import map as map_module
    if map_module.is_blocked(new_x, new_y):
        return x, y  # 被阻挡，保持原位

    return new_x, new_y
