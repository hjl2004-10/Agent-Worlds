# ============================================
# env/map_l2.py - 地图原子层
# 职责: 纯数学计算, 无状态
# ============================================

import math


def math_dist(x1, y1, x2, y2):
    """欧几里得距离计算"""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# ========== 障碍物碰撞检测 ==========

def point_in_rect(px: float, py: float, rect: dict) -> bool:
    """
    检测点是否在矩形内

    Args:
        px, py: 点坐标
        rect: {"x": 左上角x, "y": 左上角y, "width": 宽, "height": 高}

    Returns:
        True 如果点在矩形内
    """
    rx = rect["x"]
    ry = rect["y"]
    rw = rect["width"]
    rh = rect["height"]
    return rx <= px <= rx + rw and ry <= py <= ry + rh


def point_in_circle(px: float, py: float, circle: dict) -> bool:
    """
    检测点是否在圆内

    Args:
        px, py: 点坐标
        circle: {"x": 圆心x, "y": 圆心y, "radius": 半径}

    Returns:
        True 如果点在圆内
    """
    cx = circle["x"]
    cy = circle["y"]
    r = circle["radius"]
    dist = math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
    return dist <= r


def check_point_collision(px: float, py: float, obstacles: list) -> bool:
    """
    检测点是否与任意障碍物碰撞

    Args:
        px, py: 点坐标
        obstacles: 障碍物列表

    Returns:
        True 如果与任意障碍物碰撞
    """
    for obs in obstacles:
        obs_type = obs.get("type")
        if obs_type == "rect":
            if point_in_rect(px, py, obs):
                return True
        elif obs_type == "circle":
            if point_in_circle(px, py, obs):
                return True
    return False


# ========== 避障寻路辅助函数 ==========

def get_obstacle_edges(obstacle: dict) -> tuple:
    """
    获取障碍物的边界坐标

    Args:
        obstacle: 障碍物对象

    Returns:
        (left, right, top, bottom) 或 (cx, cy, r) 用于圆形
    """
    if obstacle.get("type") == "rect":
        return (
            obstacle["x"],
            obstacle["x"] + obstacle["width"],
            obstacle["y"],
            obstacle["y"] + obstacle["height"]
        )
    else:  # circle
        return (
            obstacle["x"],
            obstacle["y"],
            obstacle["radius"]
        )


def line_intersects_rect(x1, y1, x2, y2, rect_left, rect_right, rect_top, rect_bottom) -> bool:
    """
    检测线段是否与矩形相交
    使用参数化方法检测
    """
    # 快速排除: 线段完全在矩形某一侧
    if max(x1, x2) < rect_left or min(x1, x2) > rect_right:
        return False
    if max(y1, y2) < rect_top or min(y1, y2) > rect_bottom:
        return False

    # 使用 Liang-Barsky 算法的简化版
    dx = x2 - x1
    dy = y2 - y1

    p = [-dx, dx, -dy, dy]
    q = [x1 - rect_left, rect_right - x1, y1 - rect_top, rect_bottom - y1]

    u1 = 0.0
    u2 = 1.0

    for i in range(4):
        if p[i] == 0:
            if q[i] < 0:
                return False
        else:
            t = q[i] / p[i]
            if p[i] < 0:
                u1 = max(u1, t)
            else:
                u2 = min(u2, t)

    return u1 <= u2


def find_blocking_obstacle(x1, y1, x2, y2, obstacles: list) -> dict:
    """
    找到阻挡从 (x1,y1) 到 (x2,y2) 路径的第一个障碍物

    Args:
        x1, y1: 起点坐标
        x2, y2: 终点坐标
        obstacles: 障碍物列表

    Returns:
        阻挡的障碍物对象，或 None
    """
    for obs in obstacles:
        if obs.get("type") == "rect":
            edges = get_obstacle_edges(obs)
            if line_intersects_rect(x1, y1, x2, y2, *edges):
                return obs
        elif obs.get("type") == "circle":
            # 简化: 检查终点是否在圆内
            if point_in_circle(x2, y2, obs):
                return obs

    return None


def find_detour_direction(x, y, target_x, target_y, obstacle: dict) -> tuple:
    """
    根据障碍物位置计算绕行方向

    Args:
        x, y: 当前位置
        target_x, target_y: 目标位置
        obstacle: 阻挡的障碍物

    Returns:
        (dx, dy) 绕行的方向向量 (未归一化)
    """
    # 计算到目标的基础方向
    base_dx = target_x - x
    base_dy = target_y - y

    if obstacle.get("type") == "rect":
        obs_x = obstacle["x"]
        obs_y = obstacle["y"]
        obs_w = obstacle["width"]
        obs_h = obstacle["height"]
        obs_cx = obs_x + obs_w / 2
        obs_cy = obs_y + obs_h / 2

        # 判断障碍物相对于当前移动方向的位置
        # 决定从哪边绕: 上/下 或 左/右

        # 计算障碍物中心和目标中心的相对位置
        rel_x = obs_cx - x
        rel_y = obs_cy - y

        # 选择绕行方向: 垂直于障碍物的最长边
        if obs_w > obs_h:
            # 横向墙，优先从上下绕
            if base_dy > 0:
                return (0, 1)  # 向下绕
            else:
                return (0, -1)  # 向上绕
        else:
            # 纵向墙，优先从左右绕
            if base_dx > 0:
                return (1, 0)  # 向右绕
            else:
                return (-1, 0)  # 向左绕

    elif obstacle.get("type") == "circle":
        cx = obstacle["x"]
        cy = obstacle["y"]

        # 计算从圆心到当前位置的方向
        to_x = x - cx
        to_y = y - cy

        # 选择切线方向绕行 (垂直于到圆心的方向)
        # 选择更接近目标方向的切线
        tangent1 = (-to_y, to_x)  # 顺时针切线
        tangent2 = (to_y, -to_x)  # 逆时针切线

        # 选择与目标方向更一致的切线
        dot1 = tangent1[0] * base_dx + tangent1[1] * base_dy
        dot2 = tangent2[0] * base_dx + tangent2[1] * base_dy

        if dot1 > dot2:
            return tangent1
        else:
            return tangent2

    # 默认: 返回垂直于当前方向的向量
    return (-base_dy, base_dx)
