"""
core/social/conversation_task.py 单元测试 — 对话任务状态机
"""

import pytest
from unittest.mock import MagicMock


class TestConversationTask:
    """ConversationTask 创建与属性"""

    def setup_method(self):
        """每个测试前清空活跃任务列表"""
        from core.social.conversation_task import _active_tasks
        _active_tasks.clear()

    def test_create_npc_npc_task(self):
        from core.social.conversation_task import ConversationTask, ConvType, ConvState
        npc_a = MagicMock(name="Alice", is_player=False)
        npc_a.name = "Alice"
        npc_b = MagicMock(name="Bob", is_player=False)
        npc_b.name = "Bob"

        task = ConversationTask(ConvType.NPC_NPC, npc_a, npc_b)
        assert task.conv_type == ConvType.NPC_NPC
        assert task.state == ConvState.INIT
        assert task.round_count == 0
        assert task.max_rounds == 15
        assert task.is_done is False
        assert task.involves_player is False
        assert set(task.npc_names) == {"Alice", "Bob"}

    def test_create_location_task(self):
        from core.social.conversation_task import ConversationTask, ConvType
        npc = MagicMock(name="Alice", is_player=False)
        npc.name = "Alice"

        task = ConversationTask(ConvType.LOCATION, npc, location_name="办公室")
        assert task.conv_type == ConvType.LOCATION
        assert task.location_name == "办公室"
        assert task.max_rounds == 3
        assert task.npc_names == ["Alice"]

    def test_create_timer_task(self):
        from core.social.conversation_task import ConversationTask, ConvType
        npc = MagicMock(name="Bob", is_player=False)
        npc.name = "Bob"

        task = ConversationTask(ConvType.TIMER, npc, timer_desc="每日汇报")
        assert task.timer_desc == "每日汇报"

    def test_involves_player(self):
        from core.social.conversation_task import ConversationTask, ConvType
        player = MagicMock(is_player=True)
        player.name = "Player"
        npc = MagicMock(is_player=False)
        npc.name = "NPC"

        task = ConversationTask(ConvType.NPC_NPC, player, npc)
        assert task.involves_player is True


class TestTaskManager:
    """对话任务管理器"""

    def setup_method(self):
        from core.social.conversation_task import _active_tasks
        _active_tasks.clear()

    def test_create_task(self):
        from core.social.conversation_task import create_task, ConvType, get_active_count
        npc_a = MagicMock(is_player=False)
        npc_a.name = "Alice"
        npc_b = MagicMock(is_player=False)
        npc_b.name = "Bob"

        task = create_task(ConvType.NPC_NPC, npc_a, npc_b)
        assert task is not None
        assert get_active_count() == 1
        # NPC 应被冻结
        assert npc_a.is_talking is True
        assert npc_b.is_talking is True

    def test_npc_busy_prevents_creation(self):
        from core.social.conversation_task import create_task, ConvType
        npc_a = MagicMock(is_player=False)
        npc_a.name = "Alice"
        npc_b = MagicMock(is_player=False)
        npc_b.name = "Bob"
        npc_c = MagicMock(is_player=False)
        npc_c.name = "Charlie"

        # Alice 和 Bob 开始对话
        create_task(ConvType.NPC_NPC, npc_a, npc_b)
        # Alice 正忙，不能和 Charlie 对话
        task2 = create_task(ConvType.NPC_NPC, npc_a, npc_c)
        assert task2 is None

    def test_remove_task_unfreezes(self):
        from core.social.conversation_task import create_task, remove_task, ConvType, get_active_count
        npc_a = MagicMock(is_player=False)
        npc_a.name = "Alice"
        npc_b = MagicMock(is_player=False)
        npc_b.name = "Bob"

        task = create_task(ConvType.NPC_NPC, npc_a, npc_b)
        remove_task(task)
        assert get_active_count() == 0
        assert npc_a.is_talking is False
        assert npc_b.is_talking is False

    def test_clear_all(self):
        from core.social.conversation_task import create_task, clear_all, ConvType, get_active_count
        npc_a = MagicMock(is_player=False)
        npc_a.name = "A"
        npc_b = MagicMock(is_player=False)
        npc_b.name = "B"
        npc_c = MagicMock(is_player=False)
        npc_c.name = "C"

        create_task(ConvType.NPC_NPC, npc_a, npc_b)
        create_task(ConvType.LOCATION, npc_c, location_name="公园")
        assert get_active_count() == 2

        clear_all()
        assert get_active_count() == 0
        assert npc_a.is_talking is False
        assert npc_b.is_talking is False
        assert npc_c.is_talking is False

    def test_is_npc_busy(self):
        from core.social.conversation_task import create_task, is_npc_busy, ConvType
        npc_a = MagicMock(is_player=False)
        npc_a.name = "Alice"
        npc_b = MagicMock(is_player=False)
        npc_b.name = "Bob"

        assert is_npc_busy("Alice") is False
        create_task(ConvType.NPC_NPC, npc_a, npc_b)
        assert is_npc_busy("Alice") is True
        assert is_npc_busy("Bob") is True
        assert is_npc_busy("Charlie") is False
