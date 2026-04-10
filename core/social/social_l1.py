# ============================================
# core/social/social_l1.py - 交互业务层
# 职责: 个体作用域, 对话流程组装
# ============================================

import core.social.social_l2 as l2
import core.mem.mem as mem
from core import state_bus
from core.lock import conversation_lock
from tools import llm_client as llm
from core.analyzer import analyze_sync
from tools.tool import TOOL_REGISTRY
from tools.tool_l1 import invoke_custom_sync as tool_invoke_sync
from env import time as world_time
from core.prompt import prompt as prompt_module

# 玩家输入队列 (全局)
_player_input_queue = {}
_conversation_state = {"active": False, "speaker": None, "listener": None, "is_player_conversation": False}
_conversation_end_flag = False  # 结束对话标记
_npcs_ref = None  # NPC 列表引用 (由 main.py 设置)

# 最后一次对话的参与者 (用于 Ctrl+C 时保存)
# 格式: {npc_name: other_party_name}
_last_conversation_partners = {}


def set_npcs_ref(npcs):
    """设置 NPC 列表引用 (由 main.py 调用)"""
    global _npcs_ref
    _npcs_ref = npcs


def reset_runtime_state():
    """重置会话运行态，供世界/场景切换时调用。"""
    global _player_input_queue, _conversation_state, _conversation_end_flag, _last_conversation_partners
    _player_input_queue = {}
    _conversation_state = {"active": False, "speaker": None, "listener": None, "is_player_conversation": False}
    _conversation_end_flag = False
    _last_conversation_partners = {}


def set_player_input(player_name: str, text: str):
    """设置玩家输入 (由 main.py API 调用)"""
    global _player_input_queue
    with conversation_lock:
        _player_input_queue[player_name] = text
    print(f"[Player] 收到输入: {player_name} -> {text[:30]}...")


def end_conversation():
    """结束当前对话 (由前端调用)"""
    global _conversation_end_flag
    with conversation_lock:
        _conversation_end_flag = True
    print("[Player] 请求结束对话")


def wait_for_player_input(player, listener) -> str:
    """
    等待玩家输入 (轮询方式，无超时)

    Args:
        player: 玩家 NPC
        listener: 对话对象

    Returns:
        str: 玩家输入的文本，或 "[END]" 表示结束对话
    """
    import time

    player_name = player.name

    # 更新对话状态 (供前端查询) — 保留 is_player_conversation
    global _conversation_state, _conversation_end_flag
    _conversation_state.update({
        "active": True,
        "speaker": player_name,
        "listener": listener.name,
        "waiting": True,
    })

    print(f"[Player] 等待 {player_name} 输入 (与 {listener.name} 对话)...")

    while True:
        state_bus.process_all()

        with conversation_lock:
            # 检查是否请求结束
            if _conversation_end_flag:
                _conversation_end_flag = False
                _conversation_state["waiting"] = False
                return "[END]"

            # 检查是否有输入
            if player_name in _player_input_queue:
                text = _player_input_queue.pop(player_name)
                _conversation_state["waiting"] = False
                return text

        # 短暂休眠
        time.sleep(0.1)


def get_conversation_state():
    """获取当前对话状态 (供前端查询)"""
    with conversation_lock:
        return dict(_conversation_state)


def get_conversation_partners():
    """获取当前对话的配对关系 (供前端查询)"""
    with conversation_lock:
        return dict(_last_conversation_partners)


def run_conversation(npc_a, npc_b):
    """
    真实对话机制
    - 主动值高的一方先说话
    - ram_buffer 存储当前对话的 user/assistant 流
    - 双方主动值都 < 0 时结束并持久化
    - 支持工具链循环 (如果 NPC 配置了 anthropic 工具)
    - 支持玩家输入 (如果 NPC 是玩家)
    """
    global _conversation_state, _last_conversation_partners
    round_count = 0

    # 清空双方的当前对话缓存，开始新对话
    npc_a.memory['ram_buffer'] = []
    npc_b.memory['ram_buffer'] = []

    # 保存对话伙伴关系 (用于 Ctrl+C 时恢复)
    _last_conversation_partners[npc_a.name] = npc_b.name
    _last_conversation_partners[npc_b.name] = npc_a.name

    # 设置对话状态 (供前端实时显示)
    _conversation_state = {
        "active": True,
        "speaker": npc_a.name,
        "listener": npc_b.name,
        "waiting": False,
        "is_player_conversation": npc_a.is_player or npc_b.is_player,
    }

    try:
        while True:
            state_bus.process_all()
            round_count += 1

            # 1. 判定: 谁是发言者 (主动值高的)
            speaker = l2.compare_initiative(npc_a, npc_b)
            listener = npc_b if speaker == npc_a else npc_a

            # 2. 检查: 发言者主动值是否已枯竭
            if speaker.initiative < 0:
                print(f"💤 对话结束: {speaker.name} 主动值枯竭 ({speaker.initiative})")
                break

            # 3. 获取回复
            if speaker.is_player:
                # 玩家: 等待输入
                response = wait_for_player_input(speaker, listener)
                # 检查是否结束对话
                if response == "[END]":
                    print(f"🛑 玩家结束对话")
                    break
            else:
                # AI: 构建 messages 并调用 LLM
                messages, context = build_messages(speaker, listener)

                # 3.1 检查是否使用 Anthropic 工具链
                use_tools = _should_use_tools(speaker)

                if use_tools:
                    response = _chat_with_tool_loop(
                        messages, context, speaker, listener,
                        channel=speaker.llm_channel,
                        model=speaker.llm_model
                    )
                else:
                    response = llm.chat(
                        messages,
                        channel=speaker.llm_channel,
                        model=speaker.llm_model
                    )

            # 4. 输出对话
            print(f"  [{round_count}] {speaker.name}: {response}")

            # 4.5 异步分析回复内容 (仅 AI)
            if not speaker.is_player:
                analyze_sync(speaker, response, listener)
                tool_invoke_sync(speaker, response, listener)

            # 5. 更新双方的 ram_buffer (对话流)
            speaker.memory['ram_buffer'].append({"role": "assistant", "content": response})
            listener.memory['ram_buffer'].append({"role": "user", "content": response})

            # 6. 消耗主动值
            speaker.initiative -= 1
            print(f"      (主动值: {speaker.name}={speaker.initiative}, {listener.name}={listener.initiative})")

            # 7. 安全阀
            if round_count >= 15:
                print(f"⚠️ 对话轮次达到上限, 强制中断")
                break

    finally:
        # 对话结束，清理状态
        _conversation_state = {"active": False, "speaker": None, "listener": None, "is_player_conversation": False}

    # 对话结束
    finalize_conversation(npc_a, npc_b)

    # 持久化到 HJL
    mem.persist(npc_a, f"{npc_a.name.lower()}.hjl")
    mem.persist(npc_b, f"{npc_b.name.lower()}.hjl")

    return round_count


def _should_use_tools(npc) -> bool:
    """
    检查 NPC 是否应该使用 Anthropic 工具

    条件:
    - 使用 claude 协议的渠道
    - 有 rom_tools 配置 或 有待办任务需要工具
    """
    from tools import llm_l2
    from tools.task import get_pending_tasks_for

    # 1. 检查渠道是否是 claude 协议
    try:
        channel = npc.llm_channel or llm_l2.get_default_channel()
        channel_config = llm_l2.get_channel_config(channel)
        provider = channel_config.get("provider", "")

        # 只有 claude 协议才支持原生工具
        if provider != "claude":
            return False
    except Exception as e:
        print(f"[Tool] 检查渠道失败: {e}")
        return False

    # 2. 检查是否有 rom_tools 配置 (前端配置的工具)
    rom_tools = npc.memory.get('rom_tools', [])
    if rom_tools:
        return True

    # 2.5 检查是否有已连接的 MCP 工具
    mcp_tool_defs = npc.memory.get('mcp_tool_defs', [])
    if mcp_tool_defs:
        return True

    # 3. 检查是否有待办任务需要工具 (任务系统)
    pending_tasks = get_pending_tasks_for(npc.name)
    if not pending_tasks:
        return False

    for task in pending_tasks:
        if task.get('tool_hint'):
            return True

    return False


def _get_end_conversation_tool_definition():
    """获取 end_conversation 工具定义 (微信对话动态注入)"""
    from tools.tool_providers.providers import get_provider
    provider = get_provider("anthropic")
    tool_config = TOOL_REGISTRY.get("anthropic", {}).get("end_conversation", {})
    if not tool_config:
        return None
    tools = [{"name": "end_conversation", **tool_config}]
    defs = provider.get_tool_definitions(tools)
    return defs[0] if defs else None


def _get_arrived_at_tool_definition():
    """
    获取 arrived_at 工具定义 (用于地点对话时动态注入)

    Returns:
        dict: Anthropic 格式的工具定义
    """
    from tools.tool_providers.providers import get_provider

    provider = get_provider("anthropic")
    tool_config = TOOL_REGISTRY.get("anthropic", {}).get("arrived_at", {})

    if not tool_config:
        return None

    tools = [{"name": "arrived_at", **tool_config}]
    defs = provider.get_tool_definitions(tools)
    return defs[0] if defs else None


def _chat_with_tool_loop(messages, context, speaker, listener, channel, model, extra_tools=None):
    """
    带工具链循环的对话

    流程:
    1. 调用 LLM (带 tools)
    2. 如果返回 tool_use，执行工具
    3. 将结果返回给 LLM
    4. 循环直到 LLM 返回纯文本

    Args:
        messages: LLM 消息数组
        context: 上下文变量，包含 npc_tools
        speaker: 发言者 NPC
        listener: 听众 NPC
        channel: LLM 渠道
        model: 模型名称

    Returns:
        str: 最终的文本回复
    """
    from tools.tool import get_task_tool_definitions

    # 获取任务相关的工具定义
    task_tools = get_task_tool_definitions(speaker)
    # 获取 NPC 配置的工具定义 (从 context 获取，已由 prompt_l2 生成)
    npc_tools = context.get('npc_tools', [])
    # 额外的工具定义 (如地点对话的 arrived_at)
    extra = extra_tools or []

    # 合并工具列表 (去重)
    tool_names = set()
    tools = []
    for t in task_tools + npc_tools + extra:
        name = t.get("name")
        if name and name not in tool_names:
            tool_names.add(name)
            tools.append(t)

    # Skill 按需注入: 追踪已激活的技能
    activated_skills = set()
    skill_prompts = speaker.memory.get('rom_skills_prompts', {})
    tool_skill_map = speaker.memory.get('rom_tool_skill_map', {})

    # Skill 注入锁 (并发时保护 activated_skills)
    import threading
    _skill_lock = threading.Lock()

    # 单个工具执行函数 (可并发调用)
    def _execute_single_tool(tu):
        tool_name = tu.get("name")
        tool_input = tu.get("input", {})
        tool_id = tu.get("id")

        # 微信对话: 发送工具状态提示 (一轮只发一次)
        from core.wechat import wechat as wechat_module
        tool_desc = TOOL_REGISTRY.get("anthropic", {}).get(tool_name, {}).get("description", tool_name)
        wechat_module.send_tool_status(speaker, tool_name, tool_desc)

        # MCP 工具分发 (mcp__{server}__{name} 格式)
        if tool_name.startswith("mcp__"):
            from tools.mcp_client_l2 import parse_mcp_tool_name
            from tools.mcp_client import call_tool as mcp_call_tool
            server_name, actual_name = parse_mcp_tool_name(tool_name)
            if server_name:
                try:
                    result = mcp_call_tool(speaker.name, server_name, actual_name, tool_input)
                except Exception as e:
                    result = f"MCP工具错误: {e}"
            else:
                result = f"无效的MCP工具名: {tool_name}"
        else:
            # 本地工具 handler
            handler = TOOL_REGISTRY.get("anthropic", {}).get(tool_name, {}).get("handler")

            if handler:
                try:
                    ctx = {"listener": listener, "npcs": _npcs_ref}
                    result = handler(tool_input, speaker, ctx)
                    print(f"🔧 [工具执行] {tool_name}: {result[:50] if isinstance(result, str) else result}...")
                except Exception as e:
                    result = f"错误: {e}"
            else:
                result = f"未知工具: {tool_name}"

        # connect_mcp 热加载 (需串行处理，不并发)
        if tool_name == "connect_mcp":
            mcp_defs = speaker.memory.get('mcp_tool_defs', [])
            for td in mcp_defs:
                if td.get("name") not in tool_names:
                    tool_names.add(td["name"])
                    tools.append(td)
            if mcp_defs:
                print(f"🔌 [MCP] 热加载 {len(mcp_defs)} 个工具到当前对话")

        # Skill 按需注入 (加锁保护 activated_skills)
        content = str(result)
        skill_name = tool_skill_map.get(tool_name)
        if skill_name:
            with _skill_lock:
                if skill_name not in activated_skills:
                    skill_prompt = skill_prompts.get(skill_name, "")
                    if skill_prompt:
                        content = f"[技能「{skill_name}」使用指南]\n{skill_prompt}\n\n[工具执行结果]\n{content}"
                        activated_skills.add(skill_name)
                        print(f"📘 [Skill] 按需注入技能提示词: {skill_name}")

        return {
            "type": "tool_result",
            "tool_use_id": tool_id,
            "content": content
        }

    # 工具执行器 (支持并发)
    MAX_TOOL_CONCURRENCY = 5
    cancel_event = getattr(speaker, 'cancel_event', None)

    def tool_executor(tool_uses):
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # 检查取消标志
        if cancel_event and cancel_event.is_set():
            return [{
                "type": "tool_result",
                "tool_use_id": tu.get("id", ""),
                "content": "[任务已停止]"
            } for tu in tool_uses]

        # 单个工具直接执行，不开线程池
        if len(tool_uses) <= 1:
            return [_execute_single_tool(tu) for tu in tool_uses]

        # 多个工具并发执行
        results = [None] * len(tool_uses)
        workers = min(len(tool_uses), MAX_TOOL_CONCURRENCY)

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tool-exec") as pool:
            future_map = {}
            for i, tu in enumerate(tool_uses):
                # 提交前再检查一次
                if cancel_event and cancel_event.is_set():
                    break
                future = pool.submit(_execute_single_tool, tu)
                future_map[future] = i

            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = {
                        "type": "tool_result",
                        "tool_use_id": tool_uses[idx].get("id", ""),
                        "content": f"错误: 工具执行异常: {e}"
                    }

        # 填充未提交的工具结果
        for i in range(len(results)):
            if results[i] is None:
                results[i] = {
                    "type": "tool_result",
                    "tool_use_id": tool_uses[i].get("id", ""),
                    "content": "[任务已停止]"
                }

        return results

    # 调用带工具链的对话
    result = llm.chat_with_tools(
        messages=messages,
        channel=channel,
        model=model,
        tools=tools,
        tool_executor=tool_executor,
        max_tool_loops=30,
        cancel_event=cancel_event,
    )

    # 如果有工具调用记录，生成摘要存入 ram_buffer（用于记忆持久化）
    # 这样中断后下次对话时，NPC 知道上次做了什么
    tool_calls = result.get("tool_calls", [])
    if tool_calls:
        summary_lines = []
        for tc in tool_calls:
            name = tc.get("name", "unknown")
            inp = tc.get("input", {})
            # 提取关键参数作为摘要
            if name == "image_generate" or name == "image_edit":
                summary_lines.append(f"[工具] {name} → {inp.get('filename', '?')}")
            elif name == "image_to_video":
                summary_lines.append(f"[工具] {name} → {inp.get('filename', '?')}")
            elif name == "tts":
                summary_lines.append(f"[工具] {name} → {inp.get('filename', '?')}")
            elif name == "composite_image":
                summary_lines.append(f"[工具] composite_image → {inp.get('output', '?')}")
            elif name == "make_video":
                summary_lines.append(f"[工具] make_video → {inp.get('output', '?')}")
            elif name == "write_file":
                summary_lines.append(f"[工具] write_file → {inp.get('path', inp.get('filename', '?'))}")
            elif name == "invoke_npc":
                summary_lines.append(f"[工具] invoke_npc → {inp.get('target', '?')}")
            else:
                summary_lines.append(f"[工具] {name}")

        if summary_lines:
            tool_summary = "本轮执行的工具:\n" + "\n".join(summary_lines)
            speaker.memory.setdefault('ram_buffer', []).append({
                "role": "assistant",
                "content": f"[工具执行记录] {tool_summary}"
            })

    return result.get("text", "")


def build_messages(speaker, listener):
    """
    构建 LLM messages 数组和上下文

    如果 prompt 数组为空，则使用默认组装逻辑 (兼容旧数据)

    Returns:
        tuple: (messages, context)
            - messages: 可直接传给 LLM 的消息数组
            - context: 包含 npc_tools 等上下文变量
    """
    from core.prompt import prompt_l2

    prompts = speaker.memory.get('rom_prompt', [])

    # 如果有 prompt 配置，使用新模块
    if prompts:
        return prompt_module.build(speaker, listener)

    # 否则使用旧逻辑 (兼容)，但仍需生成 context
    messages = _build_messages_legacy(speaker, listener)
    context = prompt_l2.build_context(speaker, listener, {})
    return messages, context


def _build_messages_legacy(speaker, listener):
    """
    旧版 messages 构建 (兼容无 prompt 配置的旧 HJL)
    """
    messages = []

    # === 0. 第零段 system: 当前世界时间 ===
    time_info = world_time.get_time_info()
    time_str = f"当前时间: {time_info['time_str']} ({time_info['period']})"
    messages.append({"role": "system", "content": time_str})

    # === 1. 第一段 system: 人设描述 ===
    persona = speaker.memory.get('rom_personality', '')
    if persona:
        messages.append({"role": "system", "content": persona})

    # === 2. 第二段 system: 群组信息 (如果有) ===
    groups = speaker.memory.get('rom_groups', [])
    if groups:
        groups_str = "你的群组: " + ", ".join(groups)
        messages.append({"role": "system", "content": groups_str})

    # === 3. 第三段 system: 工具提示 + 额外提示 ===
    tools_prompt = speaker.memory.get('rom_tools_prompt', '')
    if tools_prompt:
        messages.append({"role": "system", "content": tools_prompt})
    extra_prompt = speaker.memory.get('rom_extra_prompt', '')
    if extra_prompt:
        messages.append({"role": "system", "content": extra_prompt})

    # === 4. 第四段 system: 历史记忆 (按对话对象过滤) ===
    history = speaker.memory.get('hdd_history', [])
    if history:
        selected = l2.select_relevant_memories(history, listener.name)
        if selected:
            history_str = "[你的记忆]:\n" + "\n".join(selected)
            messages.append({"role": "system", "content": history_str})

    # === 5. 当前对话流 (ram_buffer) ===
    chat_buffer = speaker.memory.get('ram_buffer', [])
    for msg in chat_buffer:
        messages.append(msg)

    # === 6. 确保最后一条是 user 消息 ===
    if not chat_buffer:
        history = speaker.memory.get('hdd_history', [])
        if history:
            messages.append({"role": "user", "content": f"你又遇到了{listener.name}，主动打招呼。只输出对话内容。"})
        else:
            messages.append({"role": "user", "content": f"你遇到了{listener.name}，请主动打招呼。只输出对话内容。"})
    elif chat_buffer[-1]['role'] == 'assistant':
        messages.append({"role": "user", "content": f"{listener.name}在等你继续说。只输出对话内容。"})

    return messages


def finalize_conversation(npc_a, npc_b):
    """
    对话结束时，将 ram_buffer 转换为文本记录存入 hdd_history
    """
    # 推送事件
    try:
        from api._state import push_event
        push_event("conversation_end", npc_a.name, f"{npc_a.name} 和 {npc_b.name} 结束对话")
    except Exception:
        pass
    info = world_time.get_time_info()
    timestamp = f"{info['month']}月{info['day']}日 {info['time_str']}"

    for npc, other in [(npc_a, npc_b), (npc_b, npc_a)]:
        buffer = npc.memory.get('ram_buffer', [])
        records = l2.buffer_to_history(buffer, timestamp, other.name, l2.format_conversation_record)
        npc.memory['hdd_history'].extend(records)
        npc.memory['ram_buffer'] = []


def finalize_conversation_if_needed(npc):
    """
    单个 NPC 的对话强制结束 (用于系统退出时)

    尝试从全局对话状态获取对话对象，否则使用保存的对话伙伴信息
    """
    global _conversation_state, _last_conversation_partners

    buffer = npc.memory.get('ram_buffer', [])
    if not buffer:
        return

    info = world_time.get_time_info()
    timestamp = f"{info['month']}月{info['day']}日 {info['time_str']}"

    # 尝试获取对话对象 (优先级: _conversation_state > _last_conversation_partners)
    other_name = "对方"
    if _conversation_state.get('active'):
        speaker = _conversation_state.get('speaker')
        listener = _conversation_state.get('listener')
        if npc.name == speaker and listener:
            other_name = listener
        elif npc.name == listener and speaker:
            other_name = speaker
    elif npc.name in _last_conversation_partners:
        # 使用保存的对话伙伴信息
        other_name = _last_conversation_partners[npc.name]

    for msg in buffer:
        if msg['role'] == 'assistant':
            record = f"[{timestamp}] 我对{other_name}说: {msg['content']}"
        else:
            record = f"[{timestamp}] {other_name}对我说: {msg['content']}"
        npc.memory['hdd_history'].append(record)

    npc.memory['ram_buffer'] = []
    print(f"[Finalize] {npc.name} 的对话已保存 ({len(buffer)} 条, 对象: {other_name})")


# ========== 地点碰撞对话 ==========

def run_location_conversation(npc, location_name: str):
    """
    运行 NPC 与地点的碰撞对话

    流程:
    1. 地点主动发起说话 ("你来到了广场...")
    2. NPC 回复
    3. NPC 可以调用 arrived_at 工具确认到达

    Args:
        npc: 到达地点的 NPC
        location_name: 地点名称
    """
    from env import map as map_module

    # 获取地点信息
    locations = map_module.get_all_locations()
    if location_name not in locations:
        return

    # 清空 NPC 的当前对话缓存
    npc.memory['ram_buffer'] = []

    round_count = 0
    max_rounds = 3  # 地点对话限制轮次

    try:
        while round_count < max_rounds:
            state_bus.process_all()
            round_count += 1

            # 第1轮: 地点主动发起
            if round_count == 1:
                # 地点作为 "user" 发言
                location_greeting = _generate_location_greeting(location_name, npc)
                print(f"  [{round_count}] [{location_name}]: {location_greeting}")

                # 存入 NPC 的 ram_buffer
                npc.memory['ram_buffer'].append({
                    "role": "user",
                    "content": f"[{location_name}] {location_greeting}"
                })

                # NPC 回复
                messages, context = _build_location_messages(npc, location_name)
                use_tools = _should_use_tools(npc)

                # 地点对话时，动态注入 arrived_at 工具
                arrived_at_tool = _get_arrived_at_tool_definition()

                if use_tools:
                    response = _chat_with_tool_loop(
                        messages, context, npc, None,  # context 包含 npc_tools
                        channel=npc.llm_channel,
                        model=npc.llm_model,
                        extra_tools=[arrived_at_tool]  # 注入 arrived_at
                    )
                else:
                    response = llm.chat(
                        messages,
                        channel=npc.llm_channel,
                        model=npc.llm_model
                    )

                print(f"  [{round_count}] {npc.name}: {response}")

                # 存入 ram_buffer
                npc.memory['ram_buffer'].append({"role": "assistant", "content": response})

                # 异步分析
                analyze_sync(npc, response, None)

                # 消耗主动值
                npc.initiative -= 1

            # 后续轮次: NPC 可继续回应或结束
            else:
                # 检查 NPC 主动值
                if npc.initiative < 0:
                    print(f"💤 地点对话结束: {npc.name} 主动值枯竭")
                    break

                # 检查是否已确认到达 (通过 arrived_at 工具调用后 walk_target_name 会被清除)
                if npc.walk_target_name is not None:
                    # NPC 还没确认到达，继续对话
                    pass
                else:
                    # NPC 已确认到达，结束对话
                    break

                # 构建消息让 NPC 继续回应
                messages, context = _build_location_messages(npc, location_name)

                if chat_buffer := npc.memory.get('ram_buffer', []):
                    if chat_buffer[-1]['role'] == 'assistant':
                        messages.append({
                            "role": "user",
                            "content": f"你已到达{location_name}，可以调用 arrived_at 工具确认到达，或继续观察周围。"
                        })

                use_tools = _should_use_tools(npc)
                if use_tools:
                    response = _chat_with_tool_loop(
                        messages, context, npc, None,  # context 包含 npc_tools
                        channel=npc.llm_channel,
                        model=npc.llm_model,
                        extra_tools=[arrived_at_tool]  # 注入 arrived_at
                    )
                else:
                    response = llm.chat(
                        messages,
                        channel=npc.llm_channel,
                        model=npc.llm_model
                    )

                print(f"  [{round_count}] {npc.name}: {response}")
                npc.memory['ram_buffer'].append({"role": "assistant", "content": response})

                # 消耗主动值
                npc.initiative -= 1

    finally:
        pass

    # 对话结束，保存记忆
    _finalize_location_conversation(npc, location_name)
    mem.persist(npc, f"{npc.name.lower()}.hjl")


def _generate_location_greeting(location_name: str, npc) -> str:
    """
    生成地点的问候语

    Args:
        location_name: 地点名称
        npc: 到达的 NPC

    Returns:
        str: 地点的问候语
    """
    # 从 map 模块获取问候语模板
    from env import map as map_module
    greeting_template = map_module.get_location_greeting(location_name)

    # 替换 {name} 占位符
    greeting = greeting_template.replace("{name}", npc.name)

    # 提示可以使用 arrived_at 工具
    greeting += " 如果你已到达目的地，可以调用 arrived_at 工具确认。"

    return greeting


def _build_location_messages(npc, location_name: str):
    """
    构建 NPC 与地点对话的 messages 和 context

    Args:
        npc: NPC 对象
        location_name: 地点名称

    Returns:
        tuple: (messages, context)
            - messages: LLM 消息数组
            - context: 包含 npc_tools 等上下文变量
    """
    from core.prompt import prompt, prompt_l2

    messages = []

    # 1. 当前时间
    time_info = world_time.get_time_info()
    time_str = f"当前时间: {time_info['time_str']} ({time_info['period']})"
    messages.append({"role": "system", "content": time_str})

    # 2. 人设
    persona = npc.memory.get('rom_personality', '')
    if persona:
        messages.append({"role": "system", "content": persona})

    # 3. 历史记忆 (使用统一配置: 5相关 + 3其他)
    memory_text = prompt.format_memory_for_location(npc, location_name)
    if memory_text:
        history_str = f"[你的记忆 (与{location_name}相关)]:\n{memory_text}"
        messages.append({"role": "system", "content": history_str})

    # 4. 待办任务描述
    tasks_text = prompt_l2.format_tasks(npc, None)
    if tasks_text:
        tasks_str = f"[你的待办任务]:\n{tasks_text}"
        messages.append({"role": "system", "content": tasks_str})

    # 5. 任务工具提示 (统一注入)
    task_tools_text = prompt_l2.format_task_tools(npc)
    if task_tools_text:
        messages.append({"role": "system", "content": task_tools_text})

    # 6. NPC配置工具提示
    npc_tools_text = prompt_l2.format_npc_tools(npc)
    if npc_tools_text:
        messages.append({"role": "system", "content": npc_tools_text})

    # 7. arrived_at 工具说明 (用于非 Anthropic 协议)
    if not _should_use_tools(npc):
        tools_prompt = "【地点工具】\n- arrived_at: 确认已到达指定地点，参数: location (必填，地点名称)"
        messages.append({"role": "system", "content": tools_prompt})

    # 8. 当前对话流
    chat_buffer = npc.memory.get('ram_buffer', [])
    for msg in chat_buffer:
        messages.append(msg)

    # 9. 如果没有对话流，添加初始提示
    if not chat_buffer:
        messages.append({
            "role": "user",
            "content": f"你刚刚到达了{location_name}。请回应并决定下一步。如果你已到达目的地，可以调用 arrived_at 工具确认到达。"
        })

    # 10. 生成 context (包含 npc_tools) - 地点对话没有 listener
    context = prompt_l2.build_context(npc, None, {})

    return messages, context


def _finalize_location_conversation(npc, location_name: str):
    """地点对话结束时，保存记忆"""
    info = world_time.get_time_info()
    timestamp = f"{info['month']}月{info['day']}日 {info['time_str']}"

    buffer = npc.memory.get('ram_buffer', [])
    records = l2.buffer_to_history(buffer, timestamp, location_name, l2.format_location_record)
    npc.memory['hdd_history'].extend(records)
    npc.memory['ram_buffer'] = []


# ========== 定时器对话 ==========

def run_timer_conversation(npc, description: str) -> str:
    """
    运行定时器触发的对话

    系统用 description 向 NPC 发起主动对话，
    消耗 NPC 的一次主动值。

    Args:
        npc: 目标 NPC
        description: 定时器的提示内容

    Returns:
        str: NPC 的回复
    """
    # 清空当前对话缓存
    npc.memory['ram_buffer'] = []

    # 构建消息
    messages, context = _build_timer_messages(npc, description)

    # 检查是否使用工具
    use_tools = _should_use_tools(npc)

    if use_tools:
        response = _chat_with_tool_loop(
            messages, context, npc, None,
            channel=npc.llm_channel,
            model=npc.llm_model
        )
    else:
        response = llm.chat(
            messages,
            channel=npc.llm_channel,
            model=npc.llm_model
        )

    # 存入 ram_buffer
    npc.memory['ram_buffer'].append({"role": "user", "content": f"[定时提醒] {description}"})
    npc.memory['ram_buffer'].append({"role": "assistant", "content": response})

    # 消耗主动值
    npc.initiative -= 1

    print(f"⏰ [定时器] {npc.name}: {response}")

    # 保存记忆
    _finalize_timer_conversation(npc, description)
    mem.persist(npc, f"{npc.name.lower()}.hjl")

    return response


def _build_timer_messages(npc, description: str):
    """
    构建定时器对话的 messages 和 context

    Args:
        npc: NPC 对象
        description: 定时器提示内容

    Returns:
        tuple: (messages, context)
    """
    from core.prompt import prompt, prompt_l2

    messages = []

    # 1. 当前时间
    time_info = world_time.get_time_info()
    time_str = f"当前时间: {time_info['time_str']} ({time_info['period']})"
    messages.append({"role": "system", "content": time_str})

    # 2. 人设
    persona = npc.memory.get('rom_personality', '')
    if persona:
        messages.append({"role": "system", "content": persona})

    # 3. 历史记忆 (使用统一配置: 5+3条，无相关性筛选)
    memory_text = prompt.format_memory_for_timer(npc)
    if memory_text:
        history_str = f"[你的记忆]:\n{memory_text}"
        messages.append({"role": "system", "content": history_str})

    # 4. 待办任务描述
    tasks_text = prompt_l2.format_tasks(npc, None)
    if tasks_text:
        tasks_str = f"[你的待办任务]:\n{tasks_text}"
        messages.append({"role": "system", "content": tasks_str})

    # 5. 任务工具提示 (统一注入)
    task_tools_text = prompt_l2.format_task_tools(npc)
    if task_tools_text:
        messages.append({"role": "system", "content": task_tools_text})

    # 6. NPC配置工具提示
    npc_tools_text = prompt_l2.format_npc_tools(npc)
    if npc_tools_text:
        messages.append({"role": "system", "content": npc_tools_text})

    # 7. 定时器提示 (作为 user 消息)
    messages.append({"role": "user", "content": f"[定时提醒] {description}"})

    # 8. 生成 context
    context = prompt_l2.build_context(npc, None, {})

    return messages, context


def _finalize_timer_conversation(npc, description: str):
    """定时器对话结束时，保存记忆"""
    info = world_time.get_time_info()
    timestamp = f"{info['month']}月{info['day']}日 {info['time_str']}"

    buffer = npc.memory.get('ram_buffer', [])
    records = l2.buffer_to_history(buffer, timestamp, description, l2.format_timer_record)
    npc.memory['hdd_history'].extend(records)
    npc.memory['ram_buffer'] = []


# ============================================================
# ========== 异步对话系统 (tick 驱动) ==========
# ============================================================

from core.social.conversation_task import (
    ConvState, ConvType,
    get_active_tasks, remove_task, submit_to_pool,
)


def tick_all():
    """每个主循环 tick 调用一次，推进所有活跃对话

    非阻塞: 检查每个对话的 Future 是否完成，完成则处理结果并推进状态。
    """
    global _conversation_state

    for task in list(get_active_tasks()):
        try:
            _tick_task(task)
        except Exception as e:
            print(f"❌ [Conv:{task.id}] tick 异常: {e}")
            _force_finalize(task)

        # 完成的任务清理
        if task.is_done:
            _on_task_done(task)
            remove_task(task)

    # 同步旧的 _conversation_state (前端兼容)
    active = get_active_tasks()
    if active:
        # 优先显示玩家参与的对话
        player_task = next((t for t in active if t.involves_player), None)
        show_task = player_task or active[0]
        _conversation_state = {
            "active": True,
            "speaker": show_task.speaker.name if show_task.speaker else show_task.npc_a.name,
            "listener": show_task.listener.name if show_task.listener else (show_task.npc_b.name if show_task.npc_b else None),
            "waiting": show_task.state == ConvState.WAIT_PLAYER,
            "is_player_conversation": show_task.involves_player,
        }
    else:
        _conversation_state = {"active": False, "speaker": None, "listener": None, "is_player_conversation": False}


def _tick_task(task):
    """推进单个对话任务一步"""

    if task.state == ConvState.INIT:
        _on_init(task)

    elif task.state == ConvState.NEXT_TURN:
        _on_next_turn(task)

    elif task.state == ConvState.WAIT_PLAYER:
        _on_wait_player(task)

    elif task.state == ConvState.WAIT_WECHAT:
        _on_wait_wechat(task)

    elif task.state == ConvState.CALLING_LLM:
        _on_calling_llm(task)

    elif task.state == ConvState.FINALIZING:
        task.state = ConvState.DONE


# ---------- State: INIT ----------

def _on_init(task):
    """初始化对话"""
    if task.conv_type == ConvType.NPC_NPC:
        _init_npc_conversation(task)
    elif task.conv_type == ConvType.LOCATION:
        _init_location_conversation(task)
    elif task.conv_type == ConvType.TIMER:
        _init_timer_conversation(task)
    elif task.conv_type == ConvType.WECHAT:
        _init_wechat_conversation(task)


def _init_npc_conversation(task):
    """初始化 NPC-NPC 对话"""
    npc_a, npc_b = task.npc_a, task.npc_b

    # 清空 ram_buffer
    npc_a.memory['ram_buffer'] = []
    npc_b.memory['ram_buffer'] = []

    # 保存对话伙伴
    global _last_conversation_partners
    _last_conversation_partners[npc_a.name] = npc_b.name
    _last_conversation_partners[npc_b.name] = npc_a.name

    print(f"🗣️ [Conv:{task.id}] 对话开始: {npc_a.name} <-> {npc_b.name}")

    # 推送事件
    try:
        from api._state import push_event
        push_event("conversation_start", npc_a.name, f"{npc_a.name} 和 {npc_b.name} 开始对话")
    except Exception:
        pass

    task.state = ConvState.NEXT_TURN


def _init_location_conversation(task):
    """初始化地点对话"""
    npc = task.npc_a
    npc.memory['ram_buffer'] = []

    # 第1轮: 地点发言
    location_greeting = _generate_location_greeting(task.location_name, npc)
    print(f"  [1] [{task.location_name}]: {location_greeting}")
    npc.memory['ram_buffer'].append({
        "role": "user",
        "content": f"[{task.location_name}] {location_greeting}"
    })

    task.round_count = 1
    task.speaker = npc
    task.listener = None

    # 提交 LLM 调用
    _submit_llm_call(task)


def _init_timer_conversation(task):
    """初始化定时器对话"""
    npc = task.npc_a
    npc.memory['ram_buffer'] = []

    task.round_count = 1
    task.speaker = npc
    task.listener = None

    # 提交 LLM 调用
    _submit_llm_call(task)


def _init_wechat_conversation(task):
    """初始化微信对话"""
    npc = task.npc_a
    npc.memory['ram_buffer'] = []

    # 微信消息作为第一条 user 输入
    trigger = task.wechat_trigger or "你好"
    npc.memory['ram_buffer'].append({
        "role": "user",
        "content": trigger,
        "source": "wechat",
    })

    # 设置主动值为满值
    npc.initiative = npc.max_initiative

    print(f"📱 [Conv:{task.id}] 微信对话开始: {npc.name} (触发: {trigger[:30]}...)")

    # 推送事件
    try:
        from api._state import push_event
        push_event("wechat_conversation_start", npc.name, f"{npc.name} 开始微信对话")
    except Exception:
        pass

    task.round_count = 1
    task.speaker = npc
    task.listener = None

    # NPC 回复第一条微信消息
    _submit_llm_call(task)


# ---------- State: WAIT_WECHAT ----------

def _on_wait_wechat(task):
    """检查微信用户是否已输入"""
    from core.wechat import wechat_l1

    npc = task.npc_a
    npc_name = npc.name

    text = wechat_l1.pop_wechat_input(npc_name)
    if text is None:
        return  # 没有输入，等下一个 tick

    # 收到微信输入
    npc.memory['ram_buffer'].append({
        "role": "user",
        "content": text,
        "source": "wechat",
    })

    # 重置工具状态标记
    wechat_l1.reset_tool_status(npc_name)

    # NPC 回复
    task.speaker = npc
    _submit_llm_call(task)


# ---------- State: NEXT_TURN ----------

def _on_next_turn(task):
    """准备下一轮对话"""
    task.round_count += 1

    if task.conv_type == ConvType.NPC_NPC:
        npc_a, npc_b = task.npc_a, task.npc_b

        # 检查 NPC 主动结束对话 (end_conversation 工具)
        for npc in (npc_a, npc_b):
            farewell = npc.memory.pop('_end_conversation', None)
            if farewell:
                print(f"👋 [Conv:{task.id}] {npc.name} 主动结束对话: {farewell}")
                task.state = ConvState.FINALIZING
                return

        # 判定发言者
        speaker = l2.compare_initiative(npc_a, npc_b)
        listener = npc_b if speaker == npc_a else npc_a
        task.speaker = speaker
        task.listener = listener

        # 检查主动值枯竭
        if speaker.initiative < 0:
            print(f"💤 [Conv:{task.id}] 对话结束: {speaker.name} 主动值枯竭")
            task.state = ConvState.FINALIZING
            return

        # 安全阀
        if task.round_count > task.max_rounds:
            print(f"⚠️ [Conv:{task.id}] 轮次上限，强制结束")
            task.state = ConvState.FINALIZING
            return

        # 玩家还是 AI？
        if speaker.is_player:
            task.state = ConvState.WAIT_PLAYER
        else:
            _submit_llm_call(task)

    elif task.conv_type == ConvType.LOCATION:
        npc = task.npc_a

        # 检查主动值
        if npc.initiative < 0:
            print(f"💤 [Conv:{task.id}] 地点对话结束: 主动值枯竭")
            task.state = ConvState.FINALIZING
            return

        # 检查是否已确认到达
        if npc.walk_target_name is None:
            task.state = ConvState.FINALIZING
            return

        # 安全阀
        if task.round_count > task.max_rounds:
            task.state = ConvState.FINALIZING
            return

        task.speaker = npc
        _submit_llm_call(task)

    elif task.conv_type == ConvType.WECHAT:
        npc = task.npc_a

        # 检查 NPC 主动结束对话 (end_conversation 工具)
        farewell = npc.memory.pop('_end_conversation', None)
        if farewell:
            from core.wechat import wechat_l1
            wechat_l1.send_npc_reply(npc.name, farewell)
            print(f"👋 [Conv:{task.id}] 微信对话主动结束: {npc.name} -> {farewell}")
            task.state = ConvState.FINALIZING
            return

        # 检查主动值枯竭 → 发告别消息
        if npc.initiative < 0:
            from core.wechat import wechat_l1
            wechat_l1.send_farewell(npc.name)
            print(f"💤 [Conv:{task.id}] 微信对话结束: {npc.name} 主动值枯竭")
            task.state = ConvState.FINALIZING
            return

        # 安全阀
        if task.round_count > task.max_rounds:
            from core.wechat import wechat_l1
            wechat_l1.send_farewell(npc.name)
            task.state = ConvState.FINALIZING
            return

        # 等待微信用户输入
        task.speaker = npc
        task.state = ConvState.WAIT_WECHAT


# ---------- State: WAIT_PLAYER ----------

def _on_wait_player(task):
    """检查玩家是否已输入"""
    global _conversation_end_flag

    player = task.speaker
    player_name = player.name

    # 检查结束请求 (只对玩家参与的对话生效)
    if _conversation_end_flag and task.involves_player:
        _conversation_end_flag = False
        print(f"🛑 [Conv:{task.id}] 玩家结束对话")
        task.state = ConvState.FINALIZING
        return

    # 检查输入
    if player_name in _player_input_queue:
        text = _player_input_queue.pop(player_name)

        # 玩家的发言也要存入 listener 的 ram_buffer
        listener = task.listener
        player.memory['ram_buffer'].append({"role": "assistant", "content": text})
        if listener:
            listener.memory['ram_buffer'].append({"role": "user", "content": text})

        # 消耗主动值
        player.initiative -= 1
        if listener:
            print(f"      (主动值: {player.name}={player.initiative}, {listener.name}={listener.initiative})")

        # 玩家输入不走 _process_response（不需要 analyze/tool_invoke），直接下一轮
        task.state = ConvState.NEXT_TURN
        return

    # 没有输入，等下一个 tick


# ---------- State: CALLING_LLM ----------

def _on_calling_llm(task):
    """检查 LLM Future 是否完成"""
    if task._future is None:
        # 不应该发生
        task.state = ConvState.FINALIZING
        return

    if not task._future.done():
        return  # 还没完成，等下一个 tick

    # 获取结果
    try:
        response = task._future.result()
        task._future = None
        task._pending_response = response
        _process_response(task)
    except Exception as e:
        print(f"❌ [Conv:{task.id}] LLM 调用失败: {e}")
        task._future = None
        task._pending_response = "[系统繁忙，请稍后重试]"
        _process_response(task)


# ---------- Submit LLM call ----------

def _submit_llm_call(task):
    """提交 LLM 调用到线程池"""
    task.state = ConvState.CALLING_LLM

    speaker = task.speaker
    listener = task.listener

    if task.conv_type == ConvType.NPC_NPC:
        task._future = submit_to_pool(_blocking_npc_chat, speaker, listener)
    elif task.conv_type == ConvType.LOCATION:
        task._future = submit_to_pool(_blocking_location_chat, speaker, task.location_name, task.round_count)
    elif task.conv_type == ConvType.TIMER:
        task._future = submit_to_pool(_blocking_timer_chat, speaker, task.timer_desc)
    elif task.conv_type == ConvType.WECHAT:
        task._future = submit_to_pool(_blocking_wechat_chat, speaker)


def _blocking_npc_chat(speaker, listener):
    """在线程池中执行的阻塞 LLM 调用 (NPC-NPC)"""
    messages, context = build_messages(speaker, listener)
    use_tools = _should_use_tools(speaker)

    # 注入 end_conversation 工具，让 NPC 可以主动结束对话
    end_conv_tool = _get_end_conversation_tool_definition()
    extra = [end_conv_tool] if end_conv_tool else None

    if use_tools:
        return _chat_with_tool_loop(
            messages, context, speaker, listener,
            channel=speaker.llm_channel,
            model=speaker.llm_model,
            extra_tools=extra
        )
    else:
        return llm.chat(
            messages,
            channel=speaker.llm_channel,
            model=speaker.llm_model
        )


def _blocking_location_chat(npc, location_name, round_count):
    """在线程池中执行的阻塞 LLM 调用 (地点对话)"""
    arrived_at_tool = _get_arrived_at_tool_definition()

    if round_count > 1:
        # 后续轮次
        messages, context = _build_location_messages(npc, location_name)
        if chat_buffer := npc.memory.get('ram_buffer', []):
            if chat_buffer[-1]['role'] == 'assistant':
                messages.append({
                    "role": "user",
                    "content": f"你已到达{location_name}，可以调用 arrived_at 工具确认到达，或继续观察周围。"
                })
    else:
        messages, context = _build_location_messages(npc, location_name)

    use_tools = _should_use_tools(npc)
    if use_tools:
        return _chat_with_tool_loop(
            messages, context, npc, None,
            channel=npc.llm_channel,
            model=npc.llm_model,
            extra_tools=[arrived_at_tool] if arrived_at_tool else None
        )
    else:
        return llm.chat(messages, channel=npc.llm_channel, model=npc.llm_model)


def _blocking_timer_chat(npc, description):
    """在线程池中执行的阻塞 LLM 调用 (定时器对话)"""
    messages, context = _build_timer_messages(npc, description)
    use_tools = _should_use_tools(npc)

    if use_tools:
        return _chat_with_tool_loop(
            messages, context, npc, None,
            channel=npc.llm_channel,
            model=npc.llm_model
        )
    else:
        return llm.chat(messages, channel=npc.llm_channel, model=npc.llm_model)


def _blocking_wechat_chat(npc):
    """在线程池中执行的阻塞 LLM 调用 (微信对话)

    微信对话 listener 为 None，使用虚拟 listener 构建消息。
    """
    # 构建一个虚拟 listener (微信用户)
    from body.npc import Agent
    wechat_user = Agent(name="微信用户")
    wechat_user.memory['rom_personality'] = ""

    messages, context = build_messages(npc, wechat_user)
    use_tools = _should_use_tools(npc)

    # 微信对话注入 end_conversation 工具
    end_conv_tool = _get_end_conversation_tool_definition()
    extra = [end_conv_tool] if end_conv_tool else None

    if use_tools:
        return _chat_with_tool_loop(
            messages, context, npc, None,
            channel=npc.llm_channel,
            model=npc.llm_model,
            extra_tools=extra
        )
    else:
        return llm.chat(messages, channel=npc.llm_channel, model=npc.llm_model)


def _finalize_wechat_conversation(npc):
    """微信对话结束，将 ram_buffer 转为历史记忆"""
    from env import time as wt
    info = wt.get_time_info()
    timestamp = f"{info['month']}月{info['day']}日 {info['time_str']}"

    buffer = npc.memory.get('ram_buffer', [])
    records = l2.buffer_to_history(buffer, timestamp, "微信用户", l2.format_conversation_record)
    npc.memory['hdd_history'].extend(records)
    npc.memory['ram_buffer'] = []

    # 推送事件
    try:
        from api._state import push_event
        push_event("wechat_conversation_end", npc.name, f"{npc.name} 微信对话结束")
    except Exception:
        pass


# ---------- Process response ----------

def _process_response(task):
    """处理 LLM/玩家返回的结果"""
    response = task._pending_response
    task._pending_response = None

    speaker = task.speaker
    listener = task.listener

    # 输出
    print(f"  [{task.round_count}] {speaker.name}: {response}")

    # 分析 (仅 AI)
    if not speaker.is_player:
        analyze_sync(speaker, response, listener)
        tool_invoke_sync(speaker, response, listener)

    # 更新 ram_buffer (微信对话带 source 标识)
    msg_entry = {"role": "assistant", "content": response}
    if task.conv_type == ConvType.WECHAT:
        msg_entry["source"] = "wechat"
    speaker.memory['ram_buffer'].append(msg_entry)
    if listener:
        listener_entry = {"role": "user", "content": response}
        if task.conv_type == ConvType.WECHAT:
            listener_entry["source"] = "wechat"
        listener.memory['ram_buffer'].append(listener_entry)

    # 微信对话: 推送 NPC 回复到微信
    if task.conv_type == ConvType.WECHAT:
        from core.wechat import wechat_l1
        wechat_l1.send_npc_reply(speaker.name, response)

    # 消耗主动值
    speaker.initiative -= 1
    if listener:
        print(f"      (主动值: {speaker.name}={speaker.initiative}, {listener.name}={listener.initiative})")
    else:
        print(f"      (主动值: {speaker.name}={speaker.initiative})")

    # 决定下一步
    if task.conv_type == ConvType.TIMER:
        # 定时器只有 1 轮
        task.state = ConvState.FINALIZING
    else:
        task.state = ConvState.NEXT_TURN


# ---------- Finalize ----------

def _on_task_done(task):
    """对话任务完成后的清理"""
    if task.conv_type == ConvType.NPC_NPC:
        finalize_conversation(task.npc_a, task.npc_b)
        mem.persist(task.npc_a, f"{task.npc_a.name.lower()}.hjl")
        mem.persist(task.npc_b, f"{task.npc_b.name.lower()}.hjl")

        # 设置禁止锁
        task.npc_a.ban_target_uuid = task.npc_b.name
        task.npc_b.ban_target_uuid = task.npc_a.name

        print(f"🏁 [Conv:{task.id}] 对话完成: {task.npc_a.name} <-> {task.npc_b.name} ({task.round_count} 轮)")

    elif task.conv_type == ConvType.LOCATION:
        _finalize_location_conversation(task.npc_a, task.location_name)
        mem.persist(task.npc_a, f"{task.npc_a.name.lower()}.hjl")
        print(f"🏁 [Conv:{task.id}] 地点对话完成: {task.npc_a.name} @ {task.location_name}")

    elif task.conv_type == ConvType.TIMER:
        # timer 记忆写入
        npc = task.npc_a
        npc.memory['ram_buffer'].insert(0, {"role": "user", "content": f"[定时提醒] {task.timer_desc}"})
        _finalize_timer_conversation(npc, task.timer_desc)
        mem.persist(npc, f"{npc.name.lower()}.hjl")
        print(f"🏁 [Conv:{task.id}] 定时器对话完成: {task.npc_a.name}")

    elif task.conv_type == ConvType.WECHAT:
        npc = task.npc_a
        _finalize_wechat_conversation(npc)
        mem.persist(npc, f"{npc.name.lower()}.hjl")
        # 清理微信对话上下文
        from core.wechat import wechat_l1
        wechat_l1.cleanup_wechat_context(npc.name)
        print(f"📱 [Conv:{task.id}] 微信对话完成: {npc.name} ({task.round_count} 轮)")


def _force_finalize(task):
    """异常时强制结束对话"""
    print(f"⚠️ [Conv:{task.id}] 强制结束")
    task.state = ConvState.DONE


# ---------- 对话状态查询 (供前端 API) ----------

def get_all_conversation_states():
    """获取所有活跃对话的状态 (供前端查询)

    Returns:
        list: [{"id", "type", "npcs", "state", "round", "waiting_player"}, ...]
    """
    states = []
    for task in get_active_tasks():
        states.append({
            "id": task.id,
            "type": task.conv_type.value,
            "npcs": task.npc_names,
            "state": task.state.value,
            "round": task.round_count,
            "waiting_player": task.state == ConvState.WAIT_PLAYER,
            "speaker": task.speaker.name if task.speaker else None,
            "listener": task.listener.name if task.listener else None,
        })
    return states
