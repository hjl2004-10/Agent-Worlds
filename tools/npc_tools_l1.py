# ============================================
# tools/npc_tools_l1.py - NPC 协作工具业务层
# 职责: invoke_npc (主动调用NPC) + create_npc (动态创建NPC)
# ============================================

import threading
from typing import Dict


def _tool_invoke_npc(input_obj: dict, npc, context) -> str:
    """
    主动调用另一个 NPC 执行任务

    流程:
    1. 通过 _state.find_npc 找到目标 NPC
    2. 向目标 NPC 发起一次"系统指令对话"
    3. 目标 NPC 用自己的 LLM + 工具链处理
    4. 返回结果给调用者

    Args:
        input_obj: {"target": "Alex", "message": "帮我写一篇文案", "wait": true}
        npc: 调用者 NPC
        context: 上下文
    """
    from api._state import find_npc, push_event
    from core.social import social_l1
    from core.mem import mem

    target_name = input_obj.get("target", "").strip()
    message = input_obj.get("message", "").strip()
    wait = input_obj.get("wait", True)

    if not target_name:
        return "错误: 缺少 target 参数"
    if not message:
        return "错误: 缺少 message 参数"

    # 查找目标 NPC
    target_npc = find_npc(target_name)
    if not target_npc:
        return f"错误: 未找到 NPC '{target_name}'"

    # 检查调用者是否已被取消
    caller_cancel = getattr(npc, 'cancel_event', None)
    if caller_cancel and caller_cancel.is_set():
        return "错误: 任务已被停止，取消调用"

    # 检查目标是否正在对话中，排队等待（最多等 120 秒）
    import time
    MAX_WAIT = 120
    POLL_INTERVAL = 3
    waited = 0
    if target_npc.is_talking:
        print(f"📞 [Invoke] {target_name} 正忙，排队等待...")
        while target_npc.is_talking and waited < MAX_WAIT:
            # 等待期间也检查取消
            if caller_cancel and caller_cancel.is_set():
                return "错误: 任务已被停止，取消等待"
            time.sleep(POLL_INTERVAL)
            waited += POLL_INTERVAL
        if target_npc.is_talking:
            return f"错误: {target_name} 持续忙碌超过 {MAX_WAIT} 秒，放弃调用"
        print(f"📞 [Invoke] {target_name} 已空闲 (等了 {waited}s)")

    # 推送事件
    push_event("invoke", npc.name, f"{npc.name} 调用 {target_name}: {message[:50]}")
    print(f"📞 [Invoke] {npc.name} -> {target_name}: {message[:80]}")

    if not wait:
        # 异步模式: 开线程执行，不等结果
        thread = threading.Thread(
            target=_invoke_npc_async,
            args=(npc.name, target_npc, message),
            daemon=True
        )
        thread.start()
        return f"已向 {target_name} 发送指令 (异步，不等待结果)"

    # 同步模式: 阻塞等待结果
    try:
        response = _invoke_npc_sync(npc.name, target_npc, message, caller_npc=npc)
        return f"[{target_name} 回复]\n{response}"
    except Exception as e:
        return f"错误: 调用 {target_name} 失败: {e}"


def _invoke_npc_sync(caller_name: str, target_npc, message: str, caller_npc=None) -> str:
    """
    同步调用目标 NPC (内部函数)

    类似 run_timer_conversation，但触发语来自另一个 NPC
    """
    from tools import llm
    from core.social.social_l1 import _chat_with_tool_loop, _should_use_tools, _build_timer_messages
    from core.mem import mem
    from core.prompt import prompt as prompt_module

    # 标记目标正在对话，并继承调用者的 cancel_event
    target_npc.is_talking = True
    caller_cancel = getattr(caller_npc, 'cancel_event', None) if caller_npc else None
    if caller_cancel:
        target_npc.cancel_event = caller_cancel  # 链式传递，stop 一个全停

    try:
        # 清空 ram_buffer
        target_npc.memory['ram_buffer'] = []

        # 构建消息 — 复用定时器对话的消息构建逻辑
        # 但把触发语改成 invoke 格式
        trigger = f"[来自 {caller_name} 的指令] {message}"
        messages, context_dict = _build_timer_messages(target_npc, trigger)

        # 调用 LLM
        use_tools = _should_use_tools(target_npc)

        if use_tools:
            response = _chat_with_tool_loop(
                messages, context_dict, target_npc, None,
                channel=target_npc.llm_channel,
                model=target_npc.llm_model
            )
        else:
            response = llm.chat(
                messages,
                channel=target_npc.llm_channel,
                model=target_npc.llm_model
            )

        # 存入 ram_buffer
        target_npc.memory['ram_buffer'].append({"role": "user", "content": trigger})
        target_npc.memory['ram_buffer'].append({"role": "assistant", "content": response})

        # 持久化
        mem.persist(target_npc, f"{target_npc.name.lower()}.hjl")

        print(f"📞 [Invoke] {target_npc.name} 回复: {response[:80]}")
        return response

    finally:
        target_npc.is_talking = False
        target_npc.cancel_event = None  # 清理


def _invoke_npc_async(caller_name: str, target_npc, message: str):
    """异步调用 NPC (线程入口)"""
    try:
        _invoke_npc_sync(caller_name, target_npc, message)
    except Exception as e:
        print(f"📞 [Invoke] 异步调用 {target_npc.name} 失败: {e}")


# ========== create_npc ==========

def _tool_create_npc(input_obj: dict, npc, context) -> str:
    """
    动态创建新 NPC

    流程:
    1. 校验参数 (名称不重复)
    2. 构建 HJL 数据结构
    3. 写入 HJL 文件
    4. 加载到内存 (loader_l1)
    5. 加入全局 NPC 列表

    Args:
        input_obj: {
            "name": "文案员",
            "description": "擅长写营销文案...",
            "skills": ["writer"],
            "tools": ["@file", "run_command"],
            "extra_prompt": "...",
            "llm_channel": "zhipu",
            "llm_model": "glm-5",
            "spawn_near": "Alex"
        }
    """
    from api._state import find_npc, get_npcs, push_event
    from tools import io
    from tools.loader_l1 import load_npc_from_file
    from env import map as map_module

    name = input_obj.get("name", "").strip()
    description = input_obj.get("description", "").strip()

    if not name:
        return "错误: 缺少 name 参数"
    if not description:
        return "错误: 缺少 description 参数"

    # 检查名称是否已存在
    existing = find_npc(name)
    if existing:
        return f"错误: 已存在名为 '{name}' 的 NPC"

    # 确定出生坐标 (默认在调用者旁边)
    spawn_near_name = input_obj.get("spawn_near", "")
    if spawn_near_name:
        spawn_ref = find_npc(spawn_near_name)
    else:
        spawn_ref = npc  # 默认在调用者旁边

    spawn_x = (spawn_ref.x + 16) if spawn_ref else 0
    spawn_y = spawn_ref.y if spawn_ref else 0

    # 获取当前场景信息
    scene_key = f"{map_module._current_world}:{map_module._current_scene}"

    # 构建 HJL 数据
    skills = input_obj.get("skills", [])
    tools = input_obj.get("tools", [])
    extra_prompt = input_obj.get("extra_prompt", "")
    llm_channel = input_obj.get("llm_channel", npc.llm_channel)  # 默认继承调用者的渠道
    llm_model = input_obj.get("llm_model", npc.llm_model)

    hjl_data = {
        "header": {
            "uuid": name.lower(),
            "name": name,
            "world_id": npc.world_id  # 继承调用者的世界
        },
        "position": {
            scene_key: {"x": spawn_x, "y": spawn_y}
        },
        "sprite": {"id": "Adam"},
        "attributes": {
            "description": description,
            "prompt": [],  # 使用默认提示词模板
            "skills": skills,
            "tools": tools if not skills else [],  # 有 skills 时由 skills 管理工具
            "extra_prompt": extra_prompt,
            "groups": [],
            "base_initiative": 0,
            "is_player": False,
            "no_collision": False,
            "llm_config": {
                "channel": llm_channel,
                "model": llm_model
            },
            "walk": {
                "idle_duration": 80,
                "random_duration": 10,
                "linear_duration": 50
            },
            "enabled": True,
            "mcp_servers": []
        },
        "memory": {
            "history": [],
            "note": ""
        }
    }

    # 写入 HJL 文件
    filename = f"{name.lower()}.hjl"
    try:
        io.write_hjl(filename, hjl_data)
    except Exception as e:
        return f"错误: 写入 HJL 文件失败: {e}"

    # 从文件加载到内存 (复用 loader_l1 的完整逻辑)
    try:
        new_agent = load_npc_from_file(io.DATA_PATH, filename)
        if not new_agent:
            return f"错误: 加载 NPC 失败"
    except Exception as e:
        return f"错误: 加载 NPC 失败: {e}"

    # 加入全局 NPC 列表
    npcs = get_npcs()
    npcs.append(new_agent)

    # 推送事件
    push_event("create_npc", npc.name, f"{npc.name} 创建了 NPC: {name}")

    skill_info = f", skills={skills}" if skills else ""
    tool_info = f", tools={tools}" if tools else ""
    print(f"🆕 [CreateNPC] {npc.name} 创建了 {name} @ ({spawn_x}, {spawn_y}){skill_info}{tool_info}")

    return f"已创建 NPC '{name}'，位于 ({spawn_x}, {spawn_y})，使用 {llm_channel or '默认'}渠道"
