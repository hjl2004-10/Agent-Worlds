"""
social_l2 单元测试 — 交互系统纯逻辑函数
"""

import pytest
from unittest.mock import MagicMock


class TestIsContact:
    """接触范围判断"""

    def test_within_range(self):
        from core.social.social_l2 import is_contact
        assert is_contact(1.0, 2.0) is True

    def test_at_boundary(self):
        from core.social.social_l2 import is_contact
        assert is_contact(2.0, 2.0) is True

    def test_outside_range(self):
        from core.social.social_l2 import is_contact
        assert is_contact(3.0, 2.0) is False

    def test_zero_distance(self):
        from core.social.social_l2 import is_contact
        assert is_contact(0.0, 2.0) is True

    def test_zero_limit(self):
        from core.social.social_l2 import is_contact
        assert is_contact(0.0, 0.0) is True
        assert is_contact(0.1, 0.0) is False


class TestCompareInitiative:
    """主动值比较"""

    def test_a_higher(self):
        from core.social.social_l2 import compare_initiative
        a = MagicMock(initiative=5)
        b = MagicMock(initiative=3)
        assert compare_initiative(a, b) is a

    def test_b_higher(self):
        from core.social.social_l2 import compare_initiative
        a = MagicMock(initiative=2)
        b = MagicMock(initiative=4)
        assert compare_initiative(a, b) is b

    def test_equal_a_wins(self):
        """平局时 A 有惯性优势"""
        from core.social.social_l2 import compare_initiative
        a = MagicMock(initiative=3)
        b = MagicMock(initiative=3)
        assert compare_initiative(a, b) is a


class TestShouldContinueTalking:
    """发言能量判断"""

    def test_positive_continues(self):
        from core.social.social_l2 import should_continue_talking
        assert should_continue_talking(3) is True

    def test_zero_continues(self):
        from core.social.social_l2 import should_continue_talking
        assert should_continue_talking(0) is True

    def test_negative_stops(self):
        from core.social.social_l2 import should_continue_talking
        assert should_continue_talking(-1) is False


class TestFormatConversationRecord:
    """对话记录格式化"""

    def test_self_message(self):
        from core.social.social_l2 import format_conversation_record
        result = format_conversation_record("3月18日 15:00", "Bob", "你好", True)
        assert "我对Bob说" in result
        assert "你好" in result
        assert "3月18日" in result

    def test_other_message(self):
        from core.social.social_l2 import format_conversation_record
        result = format_conversation_record("3月18日 15:00", "Bob", "嗨", False)
        assert "Bob对我说" in result
        assert "嗨" in result


class TestFormatLocationRecord:
    """地点记录格式化"""

    def test_self_reply(self):
        from core.social.social_l2 import format_location_record
        result = format_location_record("3月18日", "办公室", "我到了", True)
        assert "在办公室" in result

    def test_location_greeting(self):
        from core.social.social_l2 import format_location_record
        result = format_location_record("3月18日", "办公室", "欢迎", False)
        assert "到达办公室" in result


class TestFormatTimerRecord:
    """定时器记录格式化"""

    def test_self_reply(self):
        from core.social.social_l2 import format_timer_record
        result = format_timer_record("3月18日", "喝水提醒", "好的我去喝", True)
        assert "定时提醒" in result
        assert "喝水提醒" in result

    def test_reminder(self):
        from core.social.social_l2 import format_timer_record
        result = format_timer_record("3月18日", "检查邮件", "该检查了", False)
        assert "收到定时提醒" in result


class TestBufferToHistory:
    """ram_buffer 批量转换"""

    def test_empty_buffer(self):
        from core.social.social_l2 import buffer_to_history, format_conversation_record
        result = buffer_to_history([], "3月18日", "Bob", format_conversation_record)
        assert result == []

    def test_mixed_buffer(self):
        from core.social.social_l2 import buffer_to_history, format_conversation_record
        buffer = [
            {"role": "assistant", "content": "你好"},
            {"role": "user", "content": "嗨"},
            {"role": "assistant", "content": "再见"},
        ]
        result = buffer_to_history(buffer, "3月18日", "Bob", format_conversation_record)
        assert len(result) == 3
        assert "我对Bob说" in result[0]
        assert "Bob对我说" in result[1]
        assert "我对Bob说" in result[2]


class TestSelectRelevantMemories:
    """历史记忆筛选"""

    def test_empty_history(self):
        from core.social.social_l2 import select_relevant_memories
        assert select_relevant_memories([], "Bob") == []

    def test_all_relevant(self):
        from core.social.social_l2 import select_relevant_memories
        history = [f"和Bob聊天{i}" for i in range(10)]
        result = select_relevant_memories(history, "Bob", max_total=5)
        assert len(result) == 5

    def test_mixed_relevance(self):
        from core.social.social_l2 import select_relevant_memories
        history = ["和Alice聊天1", "和Bob聊天1", "和Alice聊天2", "和Bob聊天2"]
        result = select_relevant_memories(history, "Bob", max_relevant=5, max_total=5)
        # Bob 相关 2 条 + Alice 相关补到 5 条
        assert any("Bob" in r for r in result)

    def test_no_relevant(self):
        from core.social.social_l2 import select_relevant_memories
        history = ["和Alice聊天1", "和Alice聊天2", "和Alice聊天3"]
        result = select_relevant_memories(history, "Bob", max_total=5)
        assert len(result) == 3  # 返回全部

    def test_dict_format_compat(self):
        """兼容旧格式 dict 记忆"""
        from core.social.social_l2 import select_relevant_memories
        history = [
            {"role": "assistant", "content": "你好Bob"},
            "和Bob的文本记忆",
        ]
        result = select_relevant_memories(history, "Bob")
        assert len(result) == 2
