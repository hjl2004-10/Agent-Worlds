# ============================================
# core/dispatcher.py - 状态命令分发器
# 职责: 将 state_bus 命令路由到对应的处理函数
# ============================================

from body.npc import WalkMode
from core.lock import npcs_lock
from tools import io


# ========== 共享引用 (由 init() 注入) ==========
_npcs = None       # list[Agent]
_find_npc = None   # (name) -> Agent | None
_build_config = None  # (npc) -> dict


def init(npcs, find_npc, build_npc_config):
    """注入全局引用 (由 main.py 调用)"""
    global _npcs, _find_npc, _build_config
    _npcs = npcs
    _find_npc = find_npc
    _build_config = build_npc_config


# ========== Helper ==========

def _find_npc_or_error(payload, key="npc_name"):
    """查找 NPC，找不到返回 (None, error_response)"""
    name = payload.get(key, payload.get("npc_name", ""))
    npc = _find_npc(name)
    if not npc:
        return None, {"status": "error", "message": f"NPC '{name}' not found"}
    return npc, None


def _save_npc(npc):
    """持久化 NPC 到文件"""
    from tools import loader_l1
    loader_l1.save_npc_to_file(io.DATA_PATH, npc, f"{npc.name.lower()}.hjl")


# ========== 命令处理函数 ==========

def _cmd_player_input(payload):
    from core.social import social_l1
    social_l1.set_player_input(payload["player_name"], payload["text"])
    return {"status": "ok", "player": payload["player_name"]}


def _cmd_conversation_end(payload):
    from core.social import social_l1
    social_l1.end_conversation()
    return {"status": "ok"}


def _cmd_god_select(payload):
    npc, err = _find_npc_or_error(payload)
    if err:
        return err
    for other in _npcs:
        other.god_controlled = False
    npc.god_controlled = True
    return {"status": "ok", "selected": npc.name}


def _cmd_god_deselect(payload):
    controlled_npc = None
    for npc in _npcs:
        if npc.god_controlled:
            controlled_npc = npc
            break

    if controlled_npc:
        if "x" in payload and "y" in payload:
            controlled_npc.x = float(payload["x"])
            controlled_npc.y = float(payload["y"])
        controlled_npc.walk_mode = WalkMode.IDLE
        controlled_npc.walk_direction = 0.0
        controlled_npc.walk_mode_tick = 0
        controlled_npc.walk_target = None
        controlled_npc.walk_target_name = None

    for npc in _npcs:
        npc.god_controlled = False
        npc.god_move_direction = None

    return {"status": "ok", "committed_position": payload if "x" in payload else None}


def _cmd_god_move(payload):
    direction = payload["direction"]
    for npc in _npcs:
        if npc.god_controlled:
            npc.god_move_direction = direction
            return {"status": "ok", "npc": npc.name, "direction": direction}
    return {"status": "error", "message": "No NPC selected"}


def _cmd_god_stop(payload):
    for npc in _npcs:
        if npc.god_controlled:
            npc.god_move_direction = None
            return {"status": "ok", "npc": npc.name}
    return {"status": "ok"}


def _cmd_task_assign(payload):
    from tools import task as task_module
    task = task_module.create_task(
        hint=payload["hint"],
        source=payload.get("source", "Player"),
        tool_hint=payload.get("tool_hint"),
    )
    task_module.add_task_to_pool(payload["target"], task)
    return {"status": "ok", "task": task}


def _cmd_task_delete(payload):
    from tools import task as task_module
    deleted = task_module.remove_task_from_pool(payload["npc_name"], payload["hint"])
    return {"status": "ok", "deleted": deleted}


def _cmd_task_complete(payload):
    from tools import task as task_module
    completed = task_module.complete_task_in_pool(payload["npc_name"], payload["hint"])
    return {"status": "ok", "completed": completed}


def _cmd_timer_create(payload):
    from tools import timer as timer_module
    timer = timer_module.create_timer(
        name=payload["name"], description=payload["description"],
        target=payload["target"], interval_ticks=payload["interval_ticks"],
        max_triggers=payload["max_triggers"],
    )
    timer_module.add_timer(timer)
    return {"status": "ok", "timer": timer}


def _cmd_timer_delete(payload):
    from tools import timer as timer_module
    success = timer_module.remove_timer(payload["timer_id"])
    if success:
        return {"status": "ok", "message": f"Timer {payload['timer_id']} deleted"}
    return {"status": "error", "message": "Timer not found"}


def _cmd_timer_update(payload):
    from tools import timer as timer_module
    success = timer_module.update_timer(payload["timer_id"], payload["data"])
    if success:
        return {"status": "ok", "message": f"Timer {payload['timer_id']} updated"}
    return {"status": "error", "message": "Timer not found"}


def _cmd_inventory_update(payload):
    npc, err = _find_npc_or_error(payload)
    if err:
        return err
    data = payload["data"]
    if "schema" in data:
        npc.memory['inventory_schema'] = data["schema"]
    if "inventory" in data:
        npc.memory['inventory'] = data["inventory"]
    _save_npc(npc)
    return {
        "status": "ok", "npc": npc.name,
        "schema": npc.memory.get('inventory_schema', {}),
        "inventory": npc.memory.get('inventory', {})
    }


def _cmd_npc_tools_set(payload):
    npc, err = _find_npc_or_error(payload)
    if err:
        return err
    npc.memory['rom_tools'] = payload["tools"]
    _save_npc(npc)
    return {"status": "ok", "npc": npc.name, "tools": payload["tools"]}


def _cmd_npc_config_update(payload):
    npc, err = _find_npc_or_error(payload)
    if err:
        return err

    data = payload["data"]
    if "sprite_id" in data:
        npc.sprite_id = data["sprite_id"]
    if "description" in data:
        npc.memory['rom_personality'] = data["description"]
    if "prompt" in data:
        npc.memory['rom_prompt'] = data["prompt"]
    if "extra_prompt" in data:
        npc.memory['rom_extra_prompt'] = data["extra_prompt"]
    if "skills" in data:
        npc.memory['rom_skills'] = data["skills"]
        if data["skills"]:
            from tools.skill import resolve_skills_for_npc
            attrs = {
                "skills": data["skills"],
                "tools": data.get("tools", npc.memory.get('rom_tools', [])),
                "tools_prompt": "",  # Skill 系统自动生成，不需要手动传入
            }
            resolved_tools, summary_prompt, skill_prompts, tool_skill_map, skill_mcp = resolve_skills_for_npc(attrs)
            npc.memory['rom_tools'] = resolved_tools
            npc.memory['rom_tools_prompt'] = summary_prompt
            npc.memory['rom_skills_prompts'] = skill_prompts
            npc.memory['rom_tool_skill_map'] = tool_skill_map
            hjl_mcp = data.get("mcp_servers", npc.memory.get('mcp_servers', []))
            npc.memory['mcp_servers'] = skill_mcp + [s for s in hjl_mcp if s not in skill_mcp]
        else:
            if "tools" in data:
                npc.memory['rom_tools'] = data["tools"]
            npc.memory['rom_tools_prompt'] = ""  # 无 Skill 则清空动态工具摘要
            npc.memory['rom_skills_prompts'] = {}
            npc.memory['rom_tool_skill_map'] = {}
    elif "tools" in data:
        npc.memory['rom_tools'] = data["tools"]
    if "mcp_servers" in data:
        npc.memory['mcp_servers'] = data["mcp_servers"]
        if not data["mcp_servers"]:
            npc.memory['mcp_tool_defs'] = []
    if "groups" in data:
        npc.memory['rom_groups'] = data["groups"]
    if "llm" in data and isinstance(data["llm"], dict):
        npc.llm_channel = data["llm"].get("channel")
        npc.llm_model = data["llm"].get("model")
    if "behavior" in data and isinstance(data["behavior"], dict):
        behavior = data["behavior"]
        if "base_initiative" in behavior:
            npc.initiative = behavior["base_initiative"]
        if "walk_idle" in behavior:
            npc.walk_idle_duration = behavior["walk_idle"]
        if "walk_random" in behavior:
            npc.walk_random_duration = behavior["walk_random"]
        if "walk_linear" in behavior:
            npc.walk_linear_duration = behavior["walk_linear"]
        if "no_collision" in behavior:
            npc.memory['no_collision'] = behavior["no_collision"]
    if "enabled" in data:
        npc.enabled = data["enabled"]

    _save_npc(npc)
    return {"status": "ok", "message": f"NPC '{npc.name}' config updated", "config": _build_config(npc)}


def _cmd_npc_enabled(payload):
    npc, err = _find_npc_or_error(payload)
    if err:
        return err
    npc.enabled = payload["enabled"]
    _save_npc(npc)
    return {"status": "ok", "npc": npc.name, "enabled": payload["enabled"]}


def _cmd_npc_import(payload):
    from core.social import social_l1
    from tools import loader_l1

    imported, skipped, errors = [], [], []
    overwrite = payload.get("overwrite", False)

    with npcs_lock:
        for npc_data in payload.get("npcs", []):
            try:
                header = npc_data.get("header", {})
                name = header.get("name", "Unknown")
                existing_npc = _find_npc(name)
                if existing_npc and not overwrite:
                    skipped.append(name)
                    continue
                if existing_npc:
                    _npcs.remove(existing_npc)
                filename = f"{name.lower()}.hjl"
                io.write_hjl(filename, npc_data)
                new_npc = loader_l1.load_npc_from_file(io.DATA_PATH, filename)
                if new_npc:
                    _npcs.append(new_npc)
                    imported.append(name)
                else:
                    errors.append(f"{name}: Failed to load")
            except Exception as exc:
                errors.append(f"{npc_data.get('header', {}).get('name', 'Unknown')}: {exc}")
        social_l1.set_npcs_ref(_npcs)

    return {
        "status": "ok", "imported_count": len(imported),
        "imported": imported, "skipped": skipped,
        "errors": errors if errors else None
    }


def _cmd_npc_create(payload):
    from body.npc import Agent
    from env import map as map_module
    from core.social import social_l1
    from tools import loader_l1

    data = payload["data"]
    name = data["name"].strip()
    if _find_npc(name):
        return {"status": "error", "message": f"NPC '{name}' already exists"}

    new_npc = Agent(name=name, x=data.get("x", 100), y=data.get("y", 100))
    new_npc.sprite_id = data.get("sprite_id", "Adam")
    new_npc.world_id = data.get("world_id", map_module._current_world)
    new_npc.memory['rom_personality'] = data.get("description", "")
    if "prompt" in data:
        new_npc.memory['rom_prompt'] = data["prompt"]
    else:
        new_npc.memory['rom_prompt'] = [
            "当前时间: {time_str} ({period})", "{persona}",
            "你正在和 {listener_name} 对话。{relation_desc}",
            "{tools_prompt}", "{extra_prompt}", "{tasks_text}", "{task_tools_text}",
            "[你的记忆]:\n{memory_text}"
        ]
    new_npc.memory['rom_extra_prompt'] = data.get("extra_prompt", "")
    new_npc.memory['rom_tools'] = data.get("tools", [])
    new_npc.memory['rom_groups'] = data.get("groups", [])

    llm_config = data.get("llm", {})
    if isinstance(llm_config, dict):
        new_npc.llm_channel = llm_config.get("channel")
        new_npc.llm_model = llm_config.get("model")

    behavior = data.get("behavior", {})
    if isinstance(behavior, dict):
        new_npc.initiative = behavior.get("base_initiative", 3)
        new_npc.walk_idle_duration = behavior.get("walk_idle", 80)
        new_npc.walk_random_duration = behavior.get("walk_random", 30)
        new_npc.walk_linear_duration = behavior.get("walk_linear", 20)
    else:
        new_npc.initiative = 3

    new_npc.is_player = data.get("is_player", False)
    with npcs_lock:
        _npcs.append(new_npc)
        social_l1.set_npcs_ref(_npcs)
    loader_l1.save_npc_to_file(io.DATA_PATH, new_npc, f"{name.lower()}.hjl")
    return {
        "status": "ok", "message": f"NPC '{name}' created",
        "npc": {"name": new_npc.name, "sprite_id": new_npc.sprite_id, "x": new_npc.x, "y": new_npc.y}
    }


def _cmd_npc_export(payload):
    exported_npcs, not_found = [], []
    for name in payload["names"]:
        npc = _find_npc(name)
        if not npc:
            not_found.append(name)
            continue
        _save_npc(npc)
        npc_data = io.read_hjl(f"{npc.name.lower()}.hjl")
        if npc_data:
            exported_npcs.append(npc_data)

    if not exported_npcs:
        return {"status": "error", "message": f"No NPCs found: {not_found}"}
    return {
        "status": "ok", "exported_count": len(exported_npcs),
        "npcs": exported_npcs, "not_found": not_found if not_found else None
    }


# ========== Handler 注册表 ==========

_HANDLERS = {
    "player_input": _cmd_player_input,
    "conversation_end": _cmd_conversation_end,
    "god_select": _cmd_god_select,
    "god_deselect": _cmd_god_deselect,
    "god_move": _cmd_god_move,
    "god_stop": _cmd_god_stop,
    "task_assign": _cmd_task_assign,
    "task_delete": _cmd_task_delete,
    "task_complete": _cmd_task_complete,
    "timer_create": _cmd_timer_create,
    "timer_delete": _cmd_timer_delete,
    "timer_update": _cmd_timer_update,
    "inventory_update": _cmd_inventory_update,
    "npc_tools_set": _cmd_npc_tools_set,
    "npc_config_update": _cmd_npc_config_update,
    "npc_enabled": _cmd_npc_enabled,
    "npc_import": _cmd_npc_import,
    "npc_create": _cmd_npc_create,
    "npc_export": _cmd_npc_export,
}


def dispatch(command_type: str, payload: dict):
    """分发状态命令到对应 handler"""
    handler = _HANDLERS.get(command_type)
    if handler is None:
        raise ValueError(f"Unknown state command: {command_type}")
    return handler(payload)
