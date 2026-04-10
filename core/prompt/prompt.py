# ============================================
# core/prompt/prompt.py - 提示词总控层
# 职责: 配置定义、接口暴露
# ============================================

"""
HJL prompt 字段设计说明
======================

在 HJL 文件的 attributes 节点下新增 prompt 数组字段：

{
  "attributes": {
    "prompt": [
      "当前时间: {time_str} ({period})",
      "{persona}",
      "你正在和 {listener_name} 对话。",
      "说话要简洁。"
    ]
  }
}

【字段说明】
- prompt: 字符串数组，每个元素是一段提示词片段
- 索引从 0 开始，数组顺序即为默认组装顺序
- 支持变量占位符，格式为 {variable_name}

【预设组合】
代码中定义预设组合，通过索引选择要组装的片段：
- "full": [0, 1, 2, 3]  -> 使用全部片段
- "minimal": [0, 1]     -> 仅时间 + 人设

【层级继承】
- world.hjl 定义基础模板结构
- nation/group/individual 可覆盖或追加
- 加载时按层级合并，同索引位置后者覆盖前者

【可用变量】
- {time_str}: 当前时间字符串 (如 "08:30")
- {period}: 时段 (如 "早晨", "下午")
- {listener_name}: 对话对象名称
- {persona}: 人设描述 (从 description 字段读取)
- {tools_prompt}: 工具提示 (Skill/MCP 动态生成)
- {extra_prompt}: 额外提示 (用户手写的指令)
- {memory_text}: 格式化后的历史记忆
- {relation_desc}: 与对话对象的关系描述
"""

# ========== 预设组合配置 ==========
# key: 预设名称
# value: 索引列表 或 None
#   - None = 取 rom_prompt 数组全部项 (推荐，不受数组长度变化影响)
#   - [0, 1, ...] = 只取指定索引位置的模板行
#
# 注意: 每个 NPC 的 rom_prompt 数组长度和内容可能不同,
# 硬编码索引容易因数组变化而失效。建议 full 模式用 None。

PRESETS = {
    # 完整模式: 取全部模板行 (最安全，不受索引变化影响)
    "full": None,

    # 精简模式: 世界观 + 时间 + 人设 + 记忆 (需要确认 NPC 的数组结构)
    "minimal": [0, 1, 2],

    # 社交模式: 世界观 + 时间 + 人设 + 关系
    "social": [0, 1, 2, 3],

    # 初次见面: 世界观 + 时间 + 人设
    "first_meet": [0, 1, 2],
}

# ========== 当前激活的预设 ==========
ACTIVE_PRESET = "full"

# ========== 运行时配置 ==========
CONFIG = {
    "memory_relevant_limit": 10,     # 与对话对象/地点相关的记忆条数
    "memory_other_limit": 10,        # 其他记忆条数
    "inject_listener_brief": True,  # 是否注入对方简介
    "enable_relation_filter": True, # 是否按相关性过滤记忆
}


def build(speaker, listener, preset=None):
    """
    接口: 构建完整的 messages 数组和上下文

    Args:
        speaker: 发言者 Agent 对象
        listener: 听众 Agent 对象
        preset: 预设名称 (None 则使用 ACTIVE_PRESET)

    Returns:
        tuple: (messages, context)
            - messages: 可直接传给 LLM 的消息数组
            - context: 包含 npc_tools 等上下文变量
    """
    from core.prompt import prompt_l1
    preset_name = preset or ACTIVE_PRESET
    indices = PRESETS.get(preset_name, PRESETS["full"])
    return prompt_l1.assemble(speaker, listener, indices, CONFIG)


def get_prompt_indices(agent):
    """
    获取 Agent 的 prompt 数组长度，用于调试

    Args:
        agent: Agent 对象

    Returns:
        int: prompt 数组长度
    """
    prompts = agent.memory.get('rom_prompt', [])
    return len(prompts)


def format_memory_for_location(npc, location_name: str):
    """
    接口: 为地点对话格式化记忆

    Args:
        npc: NPC 对象
        location_name: 地点名称 (用于相关性过滤)

    Returns:
        str: 格式化后的记忆文本
    """
    from core.prompt import prompt_l2
    return prompt_l2.format_memory_by_keyword(npc, location_name, CONFIG)


def format_memory_for_timer(npc):
    """
    接口: 为定时对话格式化记忆

    Args:
        npc: NPC 对象

    Returns:
        str: 格式化后的记忆文本
    """
    from core.prompt import prompt_l2
    return prompt_l2.format_memory(npc, None, CONFIG)
