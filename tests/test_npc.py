"""
body/npc.py 单元测试 — Agent 数据容器
"""

import pytest


class TestAgentInit:
    """Agent 初始化"""

    def test_default_values(self):
        from body.npc import Agent
        npc = Agent(name="Test")
        assert npc.name == "Test"
        assert npc.x == 0
        assert npc.y == 0
        assert npc.initiative == 0
        assert npc.max_initiative == 5
        assert npc.is_talking is False
        assert npc.god_controlled is False
        from body.npc import WalkMode
        assert npc.walk_mode == WalkMode.IDLE
        assert npc.is_player is False
        assert npc.enabled is True
        assert npc.sprite_id == "Adam"
        assert npc.world_id is None

    def test_custom_position(self):
        from body.npc import Agent
        npc = Agent(name="Test", x=50.5, y=100.3)
        assert npc.x == 50.5
        assert npc.y == 100.3

    def test_memory_structure(self):
        from body.npc import Agent
        npc = Agent(name="Test")
        assert 'rom_personality' in npc.memory
        assert 'rom_prompt' in npc.memory
        assert 'ram_buffer' in npc.memory
        assert 'hdd_history' in npc.memory
        assert isinstance(npc.memory['ram_buffer'], list)
        assert isinstance(npc.memory['rom_prompt'], list)

    def test_repr(self):
        from body.npc import Agent
        npc = Agent(name="Alice", x=10.0, y=20.0)
        npc.initiative = 3
        repr_str = repr(npc)
        assert "Alice" in repr_str
        assert "10.0" in repr_str
        assert "20.0" in repr_str
