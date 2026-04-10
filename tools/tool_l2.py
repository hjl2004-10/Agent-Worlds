# ============================================
# tools/tool_l2.py - 工具调用原子层
# 职责: 纯计算、模式匹配
# ============================================

import re


def match_trigger(text, trigger):
    """
    匹配触发模式

    Args:
        text: 待匹配文本
        trigger: 触发模式
            - 普通字符串: 简单包含匹配
            - "re:xxx": 正则表达式匹配

    Returns:
        匹配结果:
            - 简单匹配: True/False
            - 正则匹配: match对象 或 None
    """
    if not text or not trigger:
        return None

    # 正则模式: 以 "re:" 开头
    if trigger.startswith("re:"):
        pattern = trigger[3:]  # 去掉 "re:" 前缀
        try:
            match = re.search(pattern, text)
            return match  # 返回 match 对象或 None
        except re.error:
            return None

    # 简单包含匹配
    if trigger in text:
        return True

    return None


def extract_params(text, pattern):
    """
    从文本中提取参数 (用于复杂工具)

    Args:
        text: 待提取文本
        pattern: 正则表达式 (带捕获组)

    Returns:
        tuple: 捕获的参数，或空元组
    """
    try:
        match = re.search(pattern, text)
        if match:
            return match.groups()
    except re.error:
        pass
    return ()


def parse_json_trigger(text, json_pattern):
    """
    解析JSON格式的触发器

    Args:
        text: 待解析文本
        json_pattern: 要匹配的JSON字符串

    Returns:
        dict: 解析后的JSON对象，或 None

    [预留] 用于复杂的JSON格式工具触发
    """
    import json
    try:
        # 在文本中查找JSON模式
        if json_pattern in text:
            # 尝试解析
            start = text.find(json_pattern)
            return json.loads(json_pattern)
    except (json.JSONDecodeError, ValueError):
        pass
    return None


# [预留] 更多原子函数:
# def validate_trigger(trigger): 验证触发模式格式
# def normalize_trigger(trigger): 标准化触发模式
# def fuzzy_match(text, keyword, threshold): 模糊匹配
