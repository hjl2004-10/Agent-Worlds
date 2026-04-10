# ============================================
# core/analyzer/analyzer_l2.py - 回复分析器原子层
# 职责: 纯计算、无状态
#
# 包含:
# - 文本模式匹配
# - 数值边界限制
# - [预留] 更复杂的NLP分析
# ============================================


def match_patterns(text, patterns):
    """
    检查文本是否包含任一模式

    Args:
        text: 待匹配文本
        patterns: 模式列表 ["模式1", "模式2", ...]

    Returns:
        bool: 是否匹配
    """
    if not text or not patterns:
        return False

    text_lower = text.lower()

    for pattern in patterns:
        if pattern.lower() in text_lower:
            return True

    return False


def match_all_patterns(text, patterns):
    """
    检查文本是否包含所有模式

    Args:
        text: 待匹配文本
        patterns: 模式列表

    Returns:
        bool: 是否全部匹配
    """
    if not text or not patterns:
        return False

    text_lower = text.lower()

    for pattern in patterns:
        if pattern.lower() not in text_lower:
            return False

    return True


def clamp(value, min_val, max_val):
    """
    将数值限制在指定范围内

    Args:
        value: 原始值
        min_val: 最小值
        max_val: 最大值

    Returns:
        限制后的值
    """
    return max(min_val, min(max_val, value))


def extract_number(text, prefix):
    """
    从文本中提取指定前缀后的数字

    例如: "主动性+3" 提取出 3
         "主动性-5" 提取出 -5

    Args:
        text: 待匹配文本
        prefix: 前缀 (如 "主动性")

    Returns:
        int or None: 提取的数字，未找到返回None

    扩展说明:
        可用于解析更精确的数值变化，如 "主动性+3" 而非固定的 +1
    """
    import re

    # 匹配 "前缀+数字" 或 "前缀-数字"
    pattern = rf"{re.escape(prefix)}([+-]?\d+)"
    match = re.search(pattern, text)

    if match:
        return int(match.group(1))

    return None


def extract_group_tags(text):
    """
    从文本中提取所有 [group:X] 标签

    例如: "[group:朋友] 我们是好朋友 [group:同事]"
         提取出 ["朋友", "同事"]

    Args:
        text: 待匹配文本

    Returns:
        list: 提取的群组名列表
    """
    import re

    # 匹配 [group:X] 格式，X 可以是任意非]字符
    pattern = r'\[group:([^\]]+)\]'
    matches = re.findall(pattern, text)

    return matches


# ============================================
# [预留] 高级分析函数
# ============================================

# def analyze_sentiment(text):
#     """
#     情感分析 (预留)
#
#     Returns:
#         float: 情感分数 -1.0 ~ 1.0
#     """
#     pass

# def extract_keywords(text):
#     """
#     关键词提取 (预留)
#
#     Returns:
#         list: 关键词列表
#     """
#     pass

# def calculate_engagement(text):
#     """
#     计算参与度 (预留)
#
#     Returns:
#         float: 参与度分数 0.0 ~ 1.0
#     """
#     pass
