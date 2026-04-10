"""
pytest 共享 fixtures
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ========== Mock map 模块 (drive_l2 依赖) ==========
# drive_l2 中有 `from env import map as map_module` 的内联导入
# 测试纯数学函数时，mock 掉 is_blocked 让它永远返回 False

import pytest


@pytest.fixture(autouse=True)
def mock_map_module():
    """Mock env.map 模块，避免 drive_l2 等模块需要真实地图数据"""
    mock_map = MagicMock()
    mock_map.is_blocked.return_value = False
    mock_map.get_obstacles.return_value = []
    mock_map.MAP_WIDTH = 500
    mock_map.MAP_HEIGHT = 500
    mock_map.LOCATIONS = {}

    with patch.dict('sys.modules', {'env.map': mock_map}):
        # 同时 mock env.map_l2
        mock_map_l2 = MagicMock()
        mock_map_l2.find_blocking_obstacle.return_value = None
        mock_map_l2.find_detour_direction.return_value = (1, 0)
        with patch.dict('sys.modules', {'env.map_l2': mock_map_l2}):
            yield mock_map


@pytest.fixture
def mock_map_blocked(mock_map_module):
    """配置 is_blocked 返回 True (障碍物测试)"""
    mock_map_module.is_blocked.return_value = True
    yield mock_map_module


@pytest.fixture
def sample_npc():
    """创建一个测试用 NPC"""
    from body.npc import Agent
    npc = Agent(name="TestNPC", x=100.0, y=100.0)
    npc.initiative = 3
    npc.max_initiative = 5
    npc.memory['rom_personality'] = "测试人设"
    npc.memory['rom_prompt'] = ["当前时间: {time_str}", "{persona}"]
    return npc


@pytest.fixture
def sample_npc_pair():
    """创建两个测试用 NPC"""
    from body.npc import Agent
    npc_a = Agent(name="Alice", x=10.0, y=10.0)
    npc_a.initiative = 3
    npc_b = Agent(name="Bob", x=12.0, y=12.0)
    npc_b.initiative = 5
    return npc_a, npc_b
