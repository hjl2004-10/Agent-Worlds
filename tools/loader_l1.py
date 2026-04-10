# ============================================
# tools/loader_l1.py - NPC加载器业务层
# 职责: 个体作用域、流程组装
# ============================================

from body.npc import Agent
from tools import io


# ========== HJL Schema 校验 ==========

# INDIVIDUAL 类型必需字段 (点分路径表示嵌套)
_INDIVIDUAL_REQUIRED = {
    "header.name": str,
}

# INDIVIDUAL 类型可选字段 (缺失时自动填入默认值)
_INDIVIDUAL_DEFAULTS = {
    "header.uuid": lambda data: str(data.get("header", {}).get("name", "unknown")).lower(),
    "position": lambda _: {},
    "sprite": lambda _: {"id": "Adam"},
    "sprite.id": lambda _: "Adam",
    "attributes": lambda _: {},
    "attributes.description": lambda _: "",
    "attributes.prompt": lambda _: [],
    "attributes.base_initiative": lambda _: 0,
    "attributes.skills": lambda _: [],
    "attributes.tools": lambda _: [],
    "attributes.groups": lambda _: [],
    "attributes.enabled": lambda _: True,
    "memory": lambda _: {},
    "memory.history": lambda _: [],
}


def validate_individual_hjl(data: dict, filename: str) -> list:
    """校验 INDIVIDUAL 类型 HJL 数据，填补缺失字段

    Args:
        data: 已解析的 HJL JSON 数据
        filename: 文件名 (用于日志)

    Returns:
        list: 警告信息列表 (空列表 = 无问题)
    """
    warnings = []

    if not isinstance(data, dict):
        warnings.append(f"[HJL校验] {filename}: 数据不是 dict 类型，跳过校验")
        return warnings

    # 检查必需字段
    for path, expected_type in _INDIVIDUAL_REQUIRED.items():
        value = _get_nested(data, path)
        if value is None:
            warnings.append(f"[HJL校验] {filename}: 缺少必需字段 '{path}'")
        elif not isinstance(value, expected_type):
            warnings.append(f"[HJL校验] {filename}: 字段 '{path}' 类型错误，期望 {expected_type.__name__}，实际 {type(value).__name__}")

    # 填补可选字段默认值
    for path, default_fn in _INDIVIDUAL_DEFAULTS.items():
        if _get_nested(data, path) is None:
            _set_nested(data, path, default_fn(data))
            warnings.append(f"[HJL校验] {filename}: 字段 '{path}' 缺失，已填入默认值")

    return warnings


def _get_nested(data: dict, path: str):
    """获取嵌套字典值，如 'header.name' -> data['header']['name']"""
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _set_nested(data: dict, path: str, value):
    """设置嵌套字典值，自动创建中间层"""
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def _get_current_scene_key():
    """获取当前 world:scene 键"""
    from env import map as map_module
    return f"{map_module._current_world}:{map_module._current_scene}"


def _resolve_position(pos_data, npc_name):
    """从 position 数据中解析当前场景的坐标

    支持两种格式:
    - 旧格式: {"x": 100, "y": 200}
    - 新格式: {"apocalypse:camp": {"x": 100, "y": 200}, "modern:office": {"x": 50, "y": 50}}
    """
    if not pos_data:
        return 0, 0, {}

    # 旧格式: 直接有 x/y 键
    if "x" in pos_data and "y" in pos_data:
        # 迁移: 当作当前场景的坐标
        scene_key = _get_current_scene_key()
        scene_positions = {scene_key: {"x": pos_data["x"], "y": pos_data["y"]}}
        return pos_data["x"], pos_data["y"], scene_positions

    # 新格式: 按场景存储
    scene_key = _get_current_scene_key()
    scene_positions = dict(pos_data)

    if scene_key in scene_positions:
        sp = scene_positions[scene_key]
        return sp.get("x", 0), sp.get("y", 0), scene_positions

    # 当前场景没有坐标, 尝试从 scene.hjl 的 spawn_points 获取
    from env import map as map_module
    spawn = _get_spawn_point(map_module.get_scene_path(), npc_name)
    if spawn:
        scene_positions[scene_key] = {"x": spawn["x"], "y": spawn["y"]}
        return spawn["x"], spawn["y"], scene_positions

    # 最终回退: 使用 default spawn 或 (0,0)
    return 0, 0, scene_positions


def _get_spawn_point(scene_path, npc_name):
    """从 scene.hjl 的 spawn_points 中获取 NPC 的出生点"""
    import json
    scene_hjl = scene_path / "scene.hjl"
    if not scene_hjl.exists():
        return None
    try:
        with open(scene_hjl, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
        spawns = scene_data.get("spawn_points", {})
        return spawns.get(npc_name, spawns.get("default"))
    except Exception:
        return None


def load_npc_from_file(data_path, filename):
    """从HJL文件加载单个NPC"""
    data = io.read_hjl(filename)
    if data is None:
        return None

    # Schema 校验 + 自动补全缺失字段
    warnings = validate_individual_hjl(data, filename)
    for w in warnings:
        print(w)

    # 校验后若仍缺必需字段，放弃加载
    if not _get_nested(data, "header.name"):
        print(f"[Loader] {filename}: header.name 缺失，跳过加载")
        return None

    # 提取数据
    header = data.get("header", {})
    attrs = data.get("attributes", {})
    pos = data.get("position", {})
    mem = data.get("memory", {})
    sprite = data.get("sprite", {})

    # 解析坐标 (支持新旧格式)
    npc_name = header.get("name", "Unknown")
    x, y, scene_positions = _resolve_position(pos, npc_name)

    # 创建Agent
    agent = Agent(
        name=npc_name,
        x=x,
        y=y
    )
    # 保存所有场景的坐标 (持久化时写回)
    agent.memory['scene_positions'] = scene_positions

    # 注入属性
    agent.initiative = attrs.get("base_initiative", 0)
    agent.memory['rom_personality'] = attrs.get("description", "")
    agent.memory['rom_prompt'] = attrs.get("prompt", [])  # 提示词模板数组
    # Skill 系统：优先从 skills 解析工具和提示词
    skills_list = attrs.get("skills", [])
    # 额外提示词 (用户手写的教学/指令，独立于工具系统)
    agent.memory['rom_extra_prompt'] = attrs.get("extra_prompt", attrs.get("tools_prompt", ""))

    if skills_list:
        from tools.skill import resolve_skills_for_npc
        resolved_tools, summary_prompt, skill_prompts, tool_skill_map, mcp_servers = resolve_skills_for_npc(attrs)
        agent.memory['rom_tools'] = resolved_tools
        agent.memory['rom_tools_prompt'] = summary_prompt          # Skill 动态生成的工具摘要
        agent.memory['rom_skills_prompts'] = skill_prompts         # {skill_name: 完整prompt} 按需注入
        agent.memory['rom_tool_skill_map'] = tool_skill_map        # {tool_name: skill_name} 反向映射
        agent.memory['mcp_servers'] = mcp_servers
    else:
        # 向后兼容：没有 skills 字段，走旧逻辑
        agent.memory['rom_tools'] = attrs.get("tools", [])
        agent.memory['rom_tools_prompt'] = ""                      # 无 Skill 则无动态工具摘要
        agent.memory['rom_skills_prompts'] = {}
        agent.memory['rom_tool_skill_map'] = {}
        agent.memory['mcp_servers'] = []
    agent.memory['rom_skills'] = skills_list

    # MCP: 合并 HJL 中直接配的 mcp_servers + Skill 中收集的 mcp_servers
    hjl_mcp_servers = attrs.get("mcp_servers", [])
    if hjl_mcp_servers:
        agent.memory['mcp_servers'] = agent.memory.get('mcp_servers', []) + hjl_mcp_servers

    # MCP: 只记录配置，不连接。NPC 可通过 connect_mcp 工具主动连接
    agent.memory['mcp_tool_defs'] = []
    if agent.memory.get('mcp_servers'):
        print(f"[MCP] {agent.name} 有 {len(agent.memory['mcp_servers'])} 个 MCP 配置 (需 NPC 主动 connect_mcp 连接)")

    agent.memory['rom_groups'] = attrs.get("groups", [])
    agent.memory['hdd_history'] = mem.get("history", [])
    agent.memory['hdd_memory_note'] = mem.get("note", "")  # NPC 个人笔记

    # 注入背包系统
    agent.memory['inventory_schema'] = attrs.get("inventory_schema", {})
    agent.memory['inventory'] = attrs.get("inventory", {})

    # 注入行走配置
    walk_config = attrs.get("walk", {})
    agent.walk_idle_duration = walk_config.get("idle_duration", 80)
    agent.walk_random_duration = walk_config.get("random_duration", 30)
    agent.walk_linear_duration = walk_config.get("linear_duration", 20)

    # 注入LLM配置
    llm_config = attrs.get("llm_config", {})
    agent.llm_channel = llm_config.get("channel", None)
    agent.llm_model = llm_config.get("model", None)

    # 注入玩家标识
    agent.is_player = attrs.get("is_player", False)

    # 注入碰撞设置
    agent.memory['no_collision'] = attrs.get("no_collision", False)

    # 注入启用状态
    agent.enabled = attrs.get("enabled", True)

    # 注入精灵图ID
    agent.sprite_id = sprite.get("id", "Adam")

    # 注入微信绑定
    wechat_binding = attrs.get("wechat_binding", {})
    if wechat_binding and wechat_binding.get("status") == "bound":
        agent.wechat_binding = wechat_binding

    # 注入世界归属 (用于多世界过滤)
    agent.world_id = header.get("world_id", None)  # None 表示全局NPC，可在任意世界出现

    player_mark = " [PLAYER]" if agent.is_player else ""
    disabled_mark = " [DISABLED]" if not agent.enabled else ""
    world_mark = f" [world:{agent.world_id}]" if agent.world_id else ""
    print(f"[Loader] {agent.name} @ ({agent.x}, {agent.y}) init={agent.initiative} walk={agent.walk_idle_duration}/{agent.walk_random_duration}/{agent.walk_linear_duration} llm={agent.llm_channel or 'default'}{player_mark}{disabled_mark}{world_mark}")
    return agent


def load_all_npcs_from_files(data_path, filenames, world_id=None):
    """批量加载NPC，可选按世界过滤

    Args:
        data_path: 数据目录路径
        filenames: 文件名列表
        world_id: 如果指定，只加载属于该世界的NPC (world_id 匹配或为 None 的全局NPC)
    """
    npcs = []
    for f in filenames:
        npc = load_npc_from_file(data_path, f)
        if npc:
            # 如果指定了 world_id，过滤 NPC
            if world_id is not None:
                # NPC 属于指定世界，或者是全局 NPC (world_id 为 None)
                if npc.world_id == world_id or npc.world_id is None:
                    npcs.append(npc)
            else:
                # 没有指定 world_id，加载所有 NPC
                npcs.append(npc)
    return npcs


def save_npc_to_file(data_path, agent, filename):
    """持久化Agent到HJL"""
    # 保存前: 把RAM刷到HDD (需要转换格式)
    ram = agent.memory.get('ram_buffer', [])
    if ram:
        # 检查 ram_buffer 内容格式，如果是 JSON 对象则转换为文本
        converted_records = []
        for msg in ram:
            if isinstance(msg, dict):
                # JSON 格式 -> 转换为文本格式
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                if role == 'assistant':
                    record = f"[对话中] 我说: {content}"
                else:
                    record = f"[对话中] 对方说: {content}"
                converted_records.append(record)
            else:
                # 已经是文本格式，直接使用
                converted_records.append(msg)

        agent.memory['hdd_history'].extend(converted_records)
        agent.memory['ram_buffer'] = []

    header = {
        "uuid": agent.name.lower(),
        "name": agent.name
    }
    if agent.world_id is not None:
        header["world_id"] = agent.world_id

    # 更新当前场景的坐标到 scene_positions
    scene_positions = agent.memory.get('scene_positions', {})
    scene_key = _get_current_scene_key()
    scene_positions[scene_key] = {"x": agent.x, "y": agent.y}

    data = {
        "header": header,
        "position": scene_positions,
        "sprite": {
            "id": agent.sprite_id
        },
        "attributes": {
            "description": agent.memory['rom_personality'],
            "prompt": agent.memory.get('rom_prompt', []),
            "skills": agent.memory.get('rom_skills', []),
            "extra_prompt": agent.memory.get('rom_extra_prompt', ''),
            "tools": agent.memory.get('rom_tools', []),
            "groups": agent.memory.get('rom_groups', []),
            "base_initiative": agent.initiative,
            "is_player": agent.is_player,
            "no_collision": agent.memory.get('no_collision', False),
            "inventory_schema": agent.memory.get('inventory_schema', {}),
            "inventory": agent.memory.get('inventory', {}),
            "walk": {
                "idle_duration": agent.walk_idle_duration,
                "random_duration": agent.walk_random_duration,
                "linear_duration": agent.walk_linear_duration
            },
            "llm_config": {
                "channel": agent.llm_channel,
                "model": agent.llm_model
            },
            "enabled": agent.enabled,
            "mcp_servers": agent.memory.get('mcp_servers', []),
            "wechat_binding": agent.wechat_binding if agent.wechat_binding.get("status") == "bound" else {},
        },
        "memory": {
            "history": agent.memory['hdd_history'],
            "note": agent.memory.get('hdd_memory_note', '')
        }
    }
    return io.write_hjl(filename, data)
