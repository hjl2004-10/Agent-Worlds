# ============================================
# env/map_l1.py - 地图业务层
# 职责: 提取NPC坐标属性, 调用L2计算, 障碍物管理
# ============================================

import json
from pathlib import Path
from typing import Optional

import env.map_l2 as l2

# ========== 障碍物数据 ==========
OBSTACLES: list = []


def load_obstacles(scene_path: Optional[Path] = None):
    """从 HJL 文件加载障碍物数据

    Args:
        scene_path: 场景目录路径，如果为 None 则使用默认路径
    """
    global OBSTACLES

    if scene_path is None:
        obstacles_file = Path(__file__).parent.parent / 'data' / 'world' / 'obstacles.hjl'
    else:
        obstacles_file = scene_path / 'obstacles.hjl'

    if not obstacles_file.exists():
        print(f"[Map] 障碍物文件不存在: {obstacles_file}")
        return

    try:
        with open(obstacles_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        OBSTACLES = data.get("obstacles", [])
        print(f"[Map] 加载 {len(OBSTACLES)} 个障碍物")
    except Exception as e:
        print(f"[Map] 加载障碍物失败: {e}")


def check_obstacle_collision(x: float, y: float) -> bool:
    """
    检查坐标是否被障碍物阻挡

    Args:
        x, y: 坐标点

    Returns:
        True 如果被阻挡
    """
    return l2.check_point_collision(x, y, OBSTACLES)


def get_all_obstacles() -> list:
    """获取所有障碍物数据"""
    return OBSTACLES.copy()


# ========== 距离计算 ==========

def calc_distance(npc_a, npc_b):
    """
    计算两个NPC之间的距离
    从NPC对象中提取坐标, 调用原子层计算
    """
    x1, y1 = npc_a.x, npc_a.y
    x2, y2 = npc_b.x, npc_b.y
    return l2.math_dist(x1, y1, x2, y2)
