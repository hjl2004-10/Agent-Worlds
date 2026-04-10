# ============================================
# core/prompt/prompt_l2.py - 提示词原子层
# 职责: 原子逻辑，纯计算，无状态
# ============================================

from env import time as world_time


def _get_mcp_tool_defs(speaker):
    """获取已连接的 MCP 工具定义

    不再自动懒加载连接。NPC 可通过 connect_mcp 工具主动连接 MCP 服务器。
    """
    return speaker.memory.get('mcp_tool_defs', [])


def build_context(speaker, listener, config):
    """
    构建模板渲染所需的上下文变量

    Args:
        speaker: 发言者 Agent
        listener: 听众 Agent
        config: 运行时配置

    Returns:
        dict: 上下文变量字典
    """
    time_info = world_time.get_time_info()
    scene_info = get_scene_info()
    scene_text = format_scene_context(scene_info)
    lore_text = format_lore()
    if scene_text:
        lore_text = f"{lore_text}\n{scene_text}" if lore_text else scene_text

    # 基础变量
    context = {
        # 时间
        'time_str': time_info['time_str'],
        'period': time_info['period'],

        # 人物
        'speaker_name': speaker.name,
        'listener_name': listener.name if listener else '未知',

        # 人设
        'persona': speaker.memory.get('rom_personality', ''),
        'tools_prompt': speaker.memory.get('rom_tools_prompt', ''),
        'extra_prompt': speaker.memory.get('rom_extra_prompt', ''),

        # 世界观
        'lore_text': lore_text,
        'lore_text': lore_text,
        'scene_text': scene_text,
        'scene_name': scene_info.get('display_name', ''),
        'scene_desc': scene_info.get('description', ''),

        # 关系
        'relation_desc': get_relation_desc(speaker, listener),

        # 记忆
        'memory_text': format_memory(speaker, listener, config),
        'memory_note': speaker.memory.get('hdd_memory_note', ''),

        # 任务
        'tasks_text': format_tasks(speaker, listener),

        # 动态工具 (根据任务注入)
        'task_tools_text': format_task_tools(speaker),

        # NPC配置工具 (根据前端 rom_tools 配置)
        # npc_tools: dict格式的工具定义 (供API层使用)
        # npc_tools_text: 文本格式的工具说明 (供提示词层注入)
        'npc_tools': get_npc_tool_definitions(speaker) + _get_mcp_tool_defs(speaker),
        'npc_tools_text': format_npc_tools(speaker),
    }

    # 条件判断变量
    context['has_persona'] = bool(context['persona'])
    context['has_tools'] = bool(context['tools_prompt'])
    context['has_extra_prompt'] = bool(context['extra_prompt'])
    context['has_memory'] = bool(speaker.memory.get('hdd_history'))
    context['has_listener'] = listener is not None
    context['has_history_with_listener'] = has_history_with(speaker, listener)
    context['has_tasks'] = bool(context['tasks_text'])
    context['has_task_tools'] = bool(context['task_tools_text'])

    return context


def render(template, context):
    """
    渲染模板字符串，替换变量占位符

    Args:
        template: 模板字符串，如 "当前时间: {time_str}"
        context: 上下文变量字典

    Returns:
        str: 渲染后的字符串
    """
    if not template:
        return ''

    result = template
    for key, value in context.items():
        placeholder = '{' + key + '}'
        if placeholder in result:
            result = result.replace(placeholder, str(value) if value else '')

    return result.strip()


def get_relation_desc(speaker, listener):
    """
    获取与对话对象的关系描述

    Args:
        speaker: 发言者
        listener: 听众

    Returns:
        str: 关系描述
    """
    if not listener:
        return ''

    groups = speaker.memory.get('rom_groups', [])
    for group in groups:
        # 格式: "关系类型:对象名" 或 "朋友:Bob"
        if ':' in group:
            rel_type, target = group.split(':', 1)
            if target == listener.name:
                return f"你们是{rel_type}关系。"

    return ''


def format_lore():
    """
    从当前世界的 world.hjl 读取并格式化世界观

    Returns:
        str: 格式化后的世界观文本
    """
    from tools import io
    from env import map as map_module

    # 动态获取当前世界的 world.hjl 路径
    world_file = map_module.get_world_path() / 'world.hjl'
    data = io.read_hjl(str(world_file))
    if not data or 'lore' not in data:
        return ''

    lore = data['lore']
    lines = []

    # 世界名称
    world_name = lore.get('world_name', '')
    if world_name:
        lines.append(f"【世界】{world_name}")

    # 背景描述
    background = lore.get('background', '')
    if background:
        lines.append(f"【背景】{background}")

    # 世界规则
    rules = lore.get('rules', [])
    if rules:
        lines.append("【规则】")
        for rule in rules:
            if rule:
                lines.append(f"- {rule}")

    # 历史事件
    history = lore.get('history', [])
    if history:
        lines.append("【历史】")
        for event in history:
            if event:
                lines.append(f"- {event}")

    return '\n'.join(lines) if lines else ''


def get_scene_info():
    """读取当前场景的基础信息。"""
    from tools import io
    from env import map as map_module

    scene_file = map_module.get_scene_path() / 'scene.hjl'
    data = io.read_hjl(str(scene_file))
    if not data:
        return {}

    return {
        'scene_id': data.get('scene_id', ''),
        'display_name': data.get('display_name', ''),
        'description': data.get('description', ''),
    }


def format_scene_context(scene_info=None):
    """格式化当前场景信息，供提示词直接复用。"""
    scene_info = scene_info or get_scene_info()
    if not scene_info:
        return ''

    lines = []
    if scene_info.get('display_name'):
        lines.append(f"【场景】{scene_info['display_name']}")
    if scene_info.get('description'):
        lines.append(f"【场景描述】{scene_info['description']}")
    return '\n'.join(lines)


def has_history_with(speaker, listener):
    """
    判断是否与听众有过对话历史

    Args:
        speaker: 发言者
        listener: 听众

    Returns:
        bool: 是否有过对话
    """
    if not listener:
        return False

    history = speaker.memory.get('hdd_history', [])
    for record in history:
        if listener.name in record:
            return True

    return False


def format_memory(speaker, listener, config):
    """
    格式化记忆历史

    记忆策略:
    - 与当前对话对象相关的记录: config['memory_relevant_limit'] 条
    - 其他记录: config['memory_other_limit'] 条

    Args:
        speaker: 发言者
        listener: 听众 (用于相关性过滤)
        config: 配置字典，包含 memory_relevant_limit 和 memory_other_limit

    Returns:
        str: 格式化后的记忆文本
    """
    relevant_limit = config.get('memory_relevant_limit', 5)
    other_limit = config.get('memory_other_limit', 3)

    history = speaker.memory.get('hdd_history', [])

    if not history:
        return ''

    # 处理可能的 dict 格式 (兼容旧数据)
    normalized = []
    for item in history:
        if isinstance(item, str):
            normalized.append(item)
        elif isinstance(item, dict):
            role = item.get('role', 'unknown')
            content = item.get('content', '')
            normalized.append(f"[{role}] {content}")

    # 如果有对话对象，分别选择相关和其他记忆
    if listener:
        # 与当前对话对象相关的记忆 (最多 relevant_limit 条)
        relevant = [r for r in normalized if listener.name in r]
        selected_relevant = relevant[-relevant_limit:] if relevant else []

        # 其他记录 (最多 other_limit 条)
        other = [r for r in normalized if listener.name not in r]
        selected_other = other[-other_limit:] if other else []

        # 合并: 相关记录 + 其他记录
        selected = selected_relevant + selected_other
    else:
        # 没有对话对象时，取最近的记录
        selected = normalized[-(relevant_limit + other_limit):]

    return '\n'.join(selected)


def format_memory_by_keyword(speaker, keyword: str, config):
    """
    按关键词格式化记忆历史 (用于地点对话)

    记忆策略:
    - 与关键词相关的记录: config['memory_relevant_limit'] 条
    - 其他记录: config['memory_other_limit'] 条

    Args:
        speaker: 发言者
        keyword: 关键词 (如地点名称)
        config: 配置字典

    Returns:
        str: 格式化后的记忆文本
    """
    relevant_limit = config.get('memory_relevant_limit', 5)
    other_limit = config.get('memory_other_limit', 3)

    history = speaker.memory.get('hdd_history', [])

    if not history:
        return ''

    # 处理可能的 dict 格式 (兼容旧数据)
    normalized = []
    for item in history:
        if isinstance(item, str):
            normalized.append(item)
        elif isinstance(item, dict):
            role = item.get('role', 'unknown')
            content = item.get('content', '')
            normalized.append(f"[{role}] {content}")

    # 与关键词相关的记忆 (最多 relevant_limit 条)
    relevant = [r for r in normalized if keyword in r]
    selected_relevant = relevant[-relevant_limit:] if relevant else []

    # 其他记录 (最多 other_limit 条)
    other = [r for r in normalized if keyword not in r]
    selected_other = other[-other_limit:] if other else []

    # 合并: 相关记录 + 其他记录
    selected = selected_relevant + selected_other

    return '\n'.join(selected)


def format_tasks(speaker, listener=None):
    """
    格式化任务提示 (自然语言，无标签)

    从全局任务池读取 pending 状态的任务

    Args:
        speaker: 发言者
        listener: 对话对象 (未使用，保留兼容)

    Returns:
        str: 任务提示文本
    """
    from tools.task import get_pending_tasks_for

    pending_tasks = get_pending_tasks_for(speaker.name)

    if not pending_tasks:
        return ''

    lines = [t.get('hint', '') for t in pending_tasks if t.get('hint')]
    return '\n'.join(lines)


def format_task_tools(speaker):
    """
    根据任务动态生成工具说明

    只处理任务池中的工具提示，不处理移动状态相关的工具。

    Args:
        speaker: 发言者

    Returns:
        str: 工具说明文本，或空字符串
    """
    from tools.task import get_pending_tasks_for

    pending_tasks = get_pending_tasks_for(speaker.name)

    # 如果没有待办任务，返回空
    if not pending_tasks:
        return ''

    # 收集需要的工具和具体参数提示
    needed_tools = set()
    tool_hints = []  # 存储具体的工具调用提示

    # 1. 从任务中提取工具
    for task in pending_tasks:
        tool_hint = task.get('tool_hint', '')
        hint = task.get('hint', '')  # 任务描述
        if tool_hint:
            # 解析工具名 (格式: "tool_name: params")
            parts = tool_hint.split(':', 1)
            tool_name = parts[0].strip()
            needed_tools.add(tool_name)

            # 保存完整的工具调用提示
            if len(parts) > 1:
                params = parts[1].strip()
                tool_hints.append(f"任务「{hint}」: {tool_name}({params})")

    # 2. 提供 complete_task 工具
    needed_tools.add('complete_task')

    # 从 TOOL_REGISTRY 动态获取工具说明
    from tools.tool import TOOL_REGISTRY

    lines = ['【可用工具】']
    for tool_name in needed_tools:
        tool_config = TOOL_REGISTRY.get("anthropic", {}).get(tool_name, {})
        if tool_config:
            # 动态生成工具说明
            desc = tool_config.get("description", "")
            schema = tool_config.get("input_schema", {})
            props = schema.get("properties", {})
            required = schema.get("required", [])

            # 格式化参数说明
            param_parts = []
            for pname, pconfig in props.items():
                req_mark = "(必填)" if pname in required else "(可选)"
                pdesc = pconfig.get("description", "")
                param_parts.append(f"{pname} {req_mark}")
                if pdesc:
                    param_parts[-1] += f" {pdesc}"

            params_str = ", ".join(param_parts) if param_parts else "无参数"
            lines.append(f"- {tool_name}: {desc}，参数: {params_str}")
        else:
            lines.append(f"- {tool_name}")

    # 添加具体的工具调用提示
    if tool_hints:
        lines.append('')
        lines.append('【工具调用提示】请使用以下参数调用工具:')
        for hint in tool_hints:
            lines.append(f"- {hint}")

    # 强调完成任务后要标记完成
    lines.append('')
    lines.append('【重要】完成任务后，请立即调用 complete_task 工具标记完成！')

    return '\n'.join(lines)


def get_npc_tool_definitions(speaker):
    """
    获取NPC配置的工具定义 (API格式)

    直接调用 tools.tool.get_anthropic_tool_definitions，
    保持单一数据源。

    Args:
        speaker: 发言者

    Returns:
        List[Dict]: Anthropic格式的工具定义列表
    """
    from tools.tool import get_anthropic_tool_definitions
    return get_anthropic_tool_definitions(speaker)


def format_npc_tools(speaker):
    """
    根据NPC前端配置的 rom_tools 生成工具说明提示词

    这是【提示词层】的工具说明，让LLM知道有哪些工具可用。
    与 format_task_tools 不同，这里是根据NPC自身的配置生成，
    而不是根据任务动态注入。

    重要：从工具注册表 TOOL_REGISTRY 动态获取，避免硬编码！

    Args:
        speaker: 发言者

    Returns:
        str: 工具说明文本，或空字符串
    """
    rom_tools = speaker.memory.get('rom_tools', [])

    if not rom_tools:
        return ''

    # 从工具注册表获取定义（避免硬编码）
    from tools.tool import TOOL_REGISTRY

    lines = ['【你的能力工具】']
    for tool_name in rom_tools:
        tool_def = TOOL_REGISTRY.get('anthropic', {}).get(tool_name)
        if tool_def:
            # 从注册表动态生成提示词
            desc = tool_def.get('description', '')
            schema = tool_def.get('input_schema', {})
            props = schema.get('properties', {})
            required = schema.get('required', [])

            # 格式化参数说明
            params = []
            for pname, pinfo in props.items():
                pdesc = pinfo.get('description', '')
                is_required = pname in required
                params.append(f"{pname}{'(必填)' if is_required else '(可选)'}: {pdesc}")

            if params:
                lines.append(f"- {tool_name}: {desc}。参数: {', '.join(params)}")
            else:
                lines.append(f"- {tool_name}: {desc}")
        else:
            # 工具不在注册表中，只显示名称
            lines.append(f"- {tool_name}")

    return '\n'.join(lines)
