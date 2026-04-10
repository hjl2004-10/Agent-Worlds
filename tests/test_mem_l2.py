"""
mem_l2 单元测试 — 记忆系统纯字符串函数
"""

import pytest


class TestFormatMemory:
    """记忆条目格式化"""

    def test_basic_format(self):
        from core.mem.mem_l2 import format_memory
        result = format_memory("2026-03-18 15:00", "Alice", "你好世界")
        assert "[2026-03-18 15:00]" in result
        assert "你好世界" in result

    def test_empty_content(self):
        from core.mem.mem_l2 import format_memory
        result = format_memory("2026-03-18", "Alice", "")
        assert "[2026-03-18]" in result


class TestSummarizeMemories:
    """记忆摘要压缩"""

    def test_empty_memories(self):
        from core.mem.mem_l2 import summarize_memories
        assert summarize_memories([]) == "无历史记忆"

    def test_single_memory(self):
        from core.mem.mem_l2 import summarize_memories
        result = summarize_memories(["事件A"])
        assert result == "事件A"

    def test_multiple_memories(self):
        from core.mem.mem_l2 import summarize_memories
        result = summarize_memories(["事件A", "事件B", "事件C"])
        assert "事件A" in result
        assert "事件B" in result
        assert " | " in result

    def test_truncation(self):
        from core.mem.mem_l2 import summarize_memories
        long_memories = [f"很长的记忆内容第{i}条" for i in range(50)]
        result = summarize_memories(long_memories, max_length=50)
        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...")

    def test_custom_max_length(self):
        from core.mem.mem_l2 import summarize_memories
        result = summarize_memories(["短"], max_length=10)
        assert result == "短"


class TestExtractKeywords:
    """关键词提取 (MVP 版直接返回原文)"""

    def test_passthrough(self):
        from core.mem.mem_l2 import extract_keywords
        assert extract_keywords("你好世界") == "你好世界"

    def test_empty_string(self):
        from core.mem.mem_l2 import extract_keywords
        assert extract_keywords("") == ""
