# ============================================
# core/prompt/prompt_l1.py - 提示词业务层
# 职责: 个体作用域，组装流程
# ============================================

from core.prompt import prompt_l2 as l2


def assemble(speaker, listener, indices, config):
    """
    组装完整的 messages 数组

    流程:
    1. 构建上下文变量
    2. 按索引选择 prompt 片段
    3. 渲染每个片段 (变量替换)
    4. 追加对话流 (ram_buffer)
    5. 追加触发语

    Args:
        speaker: 发言者 Agent
        listener: 听众 Agent
        indices: 要组装的 prompt 索引列表
        config: 运行时配置字典

    Returns:
        tuple: (messages 数组, context 上下文)
               context 包含 npc_tools 等 API 层需要的数据
    """
    messages = []

    # 1. 构建上下文变量
    context = l2.build_context(speaker, listener, config)

    # 2. 获取 prompt 模板数组
    templates = speaker.memory.get('rom_prompt', [])

    # 3. 按索引组装 system 段 (indices=None 表示取全部)
    use_indices = indices if indices is not None else range(len(templates))
    for idx in use_indices:
        if idx < len(templates):
            content = l2.render(templates[idx], context)
            if content:  # 跳过空内容
                messages.append({"role": "system", "content": content})

    # 3.5 追加动态工具提示 (根据任务的 tool_hint 注入)
    task_tools_text = context.get('task_tools_text', '')
    if task_tools_text:
        messages.append({"role": "system", "content": task_tools_text})

    # 3.6 追加NPC配置工具提示 (根据前端 rom_tools 配置)
    npc_tools_text = context.get('npc_tools_text', '')
    if npc_tools_text:
        messages.append({"role": "system", "content": npc_tools_text})

    # 4. 追加对话流 (ram_buffer)
    chat_buffer = speaker.memory.get('ram_buffer', [])
    for msg in chat_buffer:
        messages.append(msg)

    # 5. 追加触发语 (确保最后一条是 user)
    trigger = build_trigger(speaker, listener, context)
    if trigger:
        messages.append({"role": "user", "content": trigger})

    return messages, context


def build_trigger(speaker, listener, context):
    """
    构建触发语 (对话引导)

    Args:
        speaker: 发言者
        listener: 听众
        context: 上下文变量

    Returns:
        str or None: 触发语，如果不需要则返回 None
    """
    chat_buffer = speaker.memory.get('ram_buffer', [])

    if not chat_buffer:
        # 对话刚开始，需要引导语
        if context.get('has_history_with_listener'):
            return f"你又遇到了{listener.name}，主动打招呼。只输出对话内容。"
        else:
            return f"你遇到了{listener.name}，请主动打招呼。只输出对话内容。"

    elif chat_buffer[-1]['role'] == 'assistant':
        # 上一句是自己说的，需要继续
        return f"{listener.name}在等你继续说。只输出对话内容。"

    # 对话流最后已是 user 消息，无需触发语
    return None
