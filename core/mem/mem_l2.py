# ============================================
# core/mem/mem_l2.py - 记忆原子层
# 职责: 纯字符串格式化, 无状态
# ============================================


def format_memory(timestamp, name, content):
    """格式化记忆条目"""
    return f"[{timestamp}] {content}"


def summarize_memories(memories, max_length=200):
    """
    压缩记忆摘要
    用于生成精简的历史上下文
    """
    if not memories:
        return "无历史记忆"

    combined = " | ".join(memories)
    if len(combined) > max_length:
        return combined[:max_length] + "..."
    return combined


def extract_keywords(text):
    """
    从文本中提取关键词
    MVP简化版: 直接返回原文
    """
    return text
