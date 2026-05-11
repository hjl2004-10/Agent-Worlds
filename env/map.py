# ============================================
# env/map.py - 地图环境总控层
# 职责: 配置持有、接口定义
# ============================================

import json
from pathlib import Path

import env.map_l1 as l1

# ========== 配置区 ==========
# 16x16 图块制: 320x320 像素 = 20x20 图块
# 坐标系: 像素坐标 (0-320, 0-320)
# 图块坐标: 像素 / 16
TILE_SIZE = 16
MAP_WIDTH = 320   # 20 tiles
MAP_HEIGHT = 320  # 20 tiles

# 迟滞双阈值 (Hysteresis Thresholds)
THRESHOLD_CONTACT = 12.0   # 触发对话的距离 (约1个图块)
THRESHOLD_LEAVE = 24.0     # 解除禁止的距离 (约1.5个图块)

# 是否启用障碍物碰撞
OBSTACLES_ENABLED = True

# ========== 运行时状态 ==========
# 当前世界和场景 (从 runtime/current.hjl 加载)
_current_world: str = "modern"
_current_scene: str = "office"

DATA_ROOT = Path(__file__).parent.parent / 'data'
RUNTIME_FILE = DATA_ROOT / 'runtime' / 'current.hjl'


def _load_runtime_state():
    """加载运行时状态 (当前世界/场景)"""
    global _current_world, _current_scene
    if RUNTIME_FILE.exists():
        try:
            with open(RUNTIME_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            _current_world = data.get("current_world", "modern")
            _current_scene = data.get("current_scene", "office")
            print(f"[Map] 运行时状态: 世界={_current_world}, 场景={_current_scene}")
        except Exception as e:
            print(f"[Map] 加载运行时状态失败: {e}")


def init():
    """初始化地图模块 (加载运行时状态)"""
    _load_runtime_state()


def get_scene_path() -> Path:
    """获取当前场景的数据目录路径"""
    return DATA_ROOT / 'worlds' / _current_world / 'scenes' / _current_scene


def get_world_path() -> Path:
    """获取当前世界的数据目录路径"""
    return DATA_ROOT / 'worlds' / _current_world


# ========== 地点注册表 ==========
# 结构: {"地点名": {"x": x, "y": y, "desc": "描述", "greeting": "问候语"}}
LOCATIONS: dict = {}


def load_locations():
    """从 HJL 文件加载地点数据"""
    global LOCATIONS
    _load_runtime_state()

    locations_file = get_scene_path() / 'locations.hjl'
    if not locations_file.exists():
        print(f"[Map] 地点文件不存在: {locations_file}")
        return

    try:
        with open(locations_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        locs = data.get("locations", {})
        # 保存完整的地点信息 (包括 greeting)
        LOCATIONS = {
            name: {
                "x": info["x"],
                "y": info["y"],
                "building": info.get("building"),
                "desc": info.get("desc", ""),
                "greeting": info.get("greeting", ""),
                "tile": info.get("tile", [0, 0])
            }
            for name, info in locs.items()
        }
        print(f"[Map] 加载 {len(LOCATIONS)} 个地点: {list(LOCATIONS.keys())}")
    except Exception as e:
        print(f"[Map] 加载地点失败: {e}")


def load_obstacles():
    """从 HJL 文件加载障碍物数据"""
    l1.load_obstacles(get_scene_path())


# ========== 瓦片数据 ==========
TILES: list = []


def load_tiles():
    """从 HJL 文件加载地图瓦片数据"""
    global TILES
    _load_runtime_state()

    tiles_file = get_scene_path() / 'tiles.hjl'
    if not tiles_file.exists():
        print(f"[Map] 瓦片文件不存在: {tiles_file}")
        return

    try:
        with open(tiles_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        TILES = data.get("tiles", [])
        print(f"[Map] 加载 {len(TILES)}x{len(TILES[0]) if TILES else 0} 地图瓦片")
    except Exception as e:
        print(f"[Map] 加载瓦片失败: {e}")


def get_tiles() -> list:
    """获取瓦片数据 (供前端渲染)"""
    return TILES


def get_location_coords(location_name: str):
    """
    获取地点坐标

    Args:
        location_name: 地点名称

    Returns:
        (x, y) 或 None (未找到)
    """
    loc = LOCATIONS.get(location_name)
    if loc:
        return (loc["x"], loc["y"])
    return None


def get_location_greeting(location_name: str) -> str:
    """
    获取地点的问候语模板

    Args:
        location_name: 地点名称

    Returns:
        问候语模板 (可能包含 {name} 占位符)，如果未找到返回默认问候语
    """
    loc = LOCATIONS.get(location_name)
    if loc and loc.get("greeting"):
        return loc["greeting"]
    return f"你来到了{location_name}。"


def get_all_locations() -> dict:
    """获取所有地点"""
    return LOCATIONS.copy()


# ========== 障碍物接口 ==========

def is_blocked(x: float, y: float) -> bool:
    """
    检查坐标是否被障碍物阻挡

    Args:
        x, y: 坐标点

    Returns:
        True 如果被阻挡
    """
    if not OBSTACLES_ENABLED:
        return False
    return l1.check_obstacle_collision(x, y)


def get_obstacles() -> list:
    """获取所有障碍物数据 (供前端渲染)"""
    return l1.get_all_obstacles()


# ========== 接口区 ==========
def get_distance(npc_a, npc_b):
    """获取两个NPC之间的距离"""
    return l1.calc_distance(npc_a, npc_b)


def get_map_bounds():
    """获取地图边界"""
    return MAP_WIDTH, MAP_HEIGHT


def get_thresholds():
    """获取迟滞阈值"""
    return THRESHOLD_CONTACT, THRESHOLD_LEAVE
