# ============================================
# core/analyzer/analyzer.py - 回复分析器总控层
# 职责: 配置持有、接口定义
#
# 功能: 异步分析AI回复内容，识别特定模式后更新NPC属性
# 可扩展: 通过 ANALYSIS_RULES 配置新的识别规则和属性变更
# ============================================

import core.analyzer.analyzer_l1 as l1
import threading

# ========== 配置区 ==========

# 分析规则配置
# 格式: { "规则名": { "patterns": [匹配模式], "effect": {属性: 变化值} } }
#
# patterns: 关键词列表，匹配任一即触发
# effect: 属性变更字典，支持以下属性:
#   - initiative: 主动值变化 (正数增加，负数减少)
#   - [预留] mood: 情绪值变化
#   - [预留] energy: 精力值变化
#   - [预留] trust: 信任度变化
#   - [预留] 其他自定义属性...

ANALYSIS_RULES = {
    # ========== 主动性规则已停用，改为工具控制 ==========
    # 参见: tools/tool.py 中的 modify_initiative 工具
    #
    # # 正面情绪 - 主动性增加
    # "positive_engagement": {
    #     "patterns": ["主动性+", "积极", "兴奋", "开心", "太棒了", "好主意"],
    #     "effect": {"initiative": 1}
    # },
    #
    # # 负面情绪 - 主动性减少
    # "negative_feeling": {
    #     "patterns": ["主动性-", "不适", "不舒服", "反感", "厌烦", "无聊"],
    #     "effect": {"initiative": -2}
    # },
    #
    # # 强烈负面 - 主动性大幅减少
    # "strong_negative": {
    #     "patterns": ["非常不适", "极度反感", "愤怒", "生气"],
    #     "effect": {"initiative": -5}
    # },

    # [示例] 信任度变化规则 (预留)
    # "trust_increase": {
    #     "patterns": ["信任+", "相信你"],
    #     "effect": {"trust": 1}
    # },
}

# 属性边界配置
# 格式: { "属性名": (最小值, 最大值) }
ATTRIBUTE_BOUNDS = {
    "initiative": (-10, 10),
    # [预留] "mood": (-100, 100),
    # [预留] "energy": (0, 100),
    # [预留] "trust": (0, 100),
}


# ========== 接口区 ==========

def analyze_async(npc, response_text, listener=None, callback=None):
    """
    异步分析AI回复

    Args:
        npc: NPC对象 (说话者)
        response_text: AI回复的文本内容
        listener: 对话对象 (用于 group 标签绑定)
        callback: 可选回调函数，分析完成后调用 callback(npc, changes)
    """
    thread = threading.Thread(
        target=_analyze_thread,
        args=(npc, response_text, listener, callback),
        daemon=True
    )
    thread.start()
    return thread


def analyze_sync(npc, response_text, listener=None):
    """
    同步分析AI回复 (阻塞)

    Args:
        npc: NPC对象 (说话者)
        response_text: AI回复的文本内容
        listener: 对话对象 (用于 group 标签绑定)

    Returns:
        dict: 属性变更记录 {"initiative": +1, ...}
    """
    return l1.analyze_and_apply(
        npc=npc,
        text=response_text,
        rules=ANALYSIS_RULES,
        bounds=ATTRIBUTE_BOUNDS,
        listener=listener
    )


def _analyze_thread(npc, response_text, listener, callback):
    """分析线程内部函数"""
    changes = l1.analyze_and_apply(
        npc=npc,
        text=response_text,
        rules=ANALYSIS_RULES,
        bounds=ATTRIBUTE_BOUNDS,
        listener=listener
    )
    if callback and changes:
        callback(npc, changes)
