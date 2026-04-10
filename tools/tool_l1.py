# ============================================
# tools/tool_l1.py - 工具调用业务层 (L1)
# 职责: 工具处理函数、执行逻辑、协议路由
# ============================================

import threading
from typing import Any, Dict, List, Optional

from body.npc import WalkMode
from tools import tool as tool_module


# ========== 工具处理函数 ==========

# --- Custom 协议处理函数 ---

def _tool_1_test(npc, match_result, context):
    """工具1: 测试工具"""
    print(f"🔧 [工具调用] ID=1 名称=测试")
    print(f"   触发者: {npc.name}")
    return {"status": "ok", "output": "hello"}


def _tool_2_add_group(npc, match_result, context):
    """工具2: 添加群组"""
    if hasattr(match_result, 'group'):
        group_name = match_result.group(1)
    else:
        return {"status": "error", "message": "无法提取群组名"}

    # 添加到 NPC 的群组列表
    listener = context.get("listener")
    if listener:
        group_entry = f"{group_name}:{listener.name}"
        if group_entry not in npc.memory.get('rom_groups', []):
            npc.memory.setdefault('rom_groups', []).append(group_entry)
            print(f"🏷️ [群组] {npc.name} -> {group_entry}")

    return {"status": "ok", "group": group_name}


# --- Anthropic 协议处理函数 ---

def _normalize_path(path: str) -> str:
    """清理路径，去掉 workspace/ 前缀"""
    # 去掉开头的 workspace/ 或 workspace\
    if path.startswith("workspace/") or path.startswith("workspace\\"):
        path = path[9:]  # len("workspace/") = 9
    # 去掉开头的 / 或 \
    path = path.lstrip("/\\")
    return path


def _resolve_safe_path(path: str):
    """解析路径并检查权限

    支持:
    - 相对路径 (相对于 workspace): "test.py" → workspace/test.py
    - data/ 开头的路径: "data/skills/..." → 项目根/data/skills/...
    - 绝对路径: 直接检查是否在允许范围内

    Returns:
        (Path, None) 成功 或 (None, 错误信息) 失败
    """
    from pathlib import Path

    workdir = tool_module.WORKDIR or Path.cwd()
    project_root = tool_module.PROJECT_ROOT or workdir.parent

    # 绝对路径直接用
    if Path(path).is_absolute():
        fp = Path(path).resolve()
    # data/ 开头 → 相对项目根
    elif path.startswith("data/") or path.startswith("data\\"):
        fp = (project_root / path).resolve()
    # 其他 → 相对 workspace
    else:
        normalized = _normalize_path(path)
        fp = (workdir / normalized).resolve()

    if not tool_module.is_path_allowed(fp):
        return None, f"错误: 路径不在允许范围内: {path}"

    return fp, None


def _tool_read_file(input_obj: dict, npc, context) -> str:
    """读取文件 (支持纯文本 + PDF/DOCX/PPTX/Excel/CSV/图片)"""
    path = input_obj.get("path", "")
    fp, err = _resolve_safe_path(path)
    if err:
        return err

    if not fp.exists():
        return f"错误: 文件不存在: {path}"

    if fp.is_dir():
        # 目录: 列出文件 (避免 Permission denied)
        items = sorted(fp.iterdir())
        listing = "\n".join(f"  {'[目录]' if p.is_dir() else f'{p.stat().st_size/1024:.1f}KB'} {p.name}" for p in items[:50])
        return f"[目录] {path} ({len(items)} 个项目):\n{listing}"

    max_chars = min(int(input_obj.get("max_chars", 100000)), 200000)

    # 文档格式 → 特殊解析
    from tools.document_l2 import is_document, extract_text
    if is_document(fp):
        try:
            text, hint = extract_text(fp, max_chars)
            if not text and hint:
                return f"错误: {hint}"
            print(f"📖 [读取文档] {path} ({hint})")
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n\n...<截断>"
            return f"[{hint}]\n\n{text}"
        except Exception as e:
            return f"错误: 读取文档失败: {e}"

    # 纯文本
    try:
        text = fp.read_text("utf-8")
        lines = text.split("\n")

        # 处理行范围
        start = (max(1, int(input_obj.get("start_line", 1))) - 1)
        end_line = input_obj.get("end_line")
        if isinstance(end_line, int):
            end = len(lines) if end_line < 0 else max(start, end_line)
        else:
            end = len(lines)

        text = "\n".join(lines[start:end])

        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n...<截断 {len(text) - max_chars} 字符>"

        print(f"📖 [读取文件] {path}")
        return text

    except UnicodeDecodeError:
        # 二进制文件
        size = fp.stat().st_size
        return f"[二进制文件] {path}\n大小: {size / 1024:.1f} KB\n扩展名: {fp.suffix}\n(无法作为文本读取)"
    except Exception as e:
        return f"错误: {e}"


def _tool_write_file(input_obj: dict, npc, context) -> str:
    """写入文件"""
    path = input_obj.get("path", "")
    content = input_obj.get("content", "")
    mode = input_obj.get("mode", "overwrite")

    fp, err = _resolve_safe_path(path)
    if err:
        return err

    try:

        fp.parent.mkdir(parents=True, exist_ok=True)

        if mode == "append" and fp.exists():
            with fp.open("a", encoding="utf-8") as f:
                f.write(content)
        else:
            fp.write_text(content, encoding="utf-8")

        bytes_len = len(content.encode("utf-8"))
        print(f"📝 [写入文件] {path} ({bytes_len} 字节)")
        return f"已写入 {bytes_len} 字节到 {path}"

    except Exception as e:
        return f"错误: {e}"


def _tool_delete_file(input_obj: dict, npc, context) -> str:
    """删除文件"""
    path = input_obj.get("path", "")
    fp, err = _resolve_safe_path(path)
    if err:
        return err

    try:

        if not fp.exists():
            return f"错误: 文件不存在 {path}"

        if fp.is_dir():
            return f"错误: {path} 是目录，不是文件"

        fp.unlink()
        print(f"🗑️ [删除文件] {path}")
        return f"已删除文件 {path}"

    except Exception as e:
        return f"错误: {e}"


def _tool_edit_text(input_obj: dict, npc, context) -> str:
    """编辑文件"""
    path = input_obj.get("path", "")
    action = input_obj.get("action")

    fp, err = _resolve_safe_path(path)
    if err:
        return err

    try:

        text = fp.read_text("utf-8")

        if action == "replace":
            find = str(input_obj.get("find", ""))
            if not find:
                return "错误: 缺少 find 参数"
            replaced = text.replace(find, str(input_obj.get("replace", "")))
            fp.write_text(replaced, encoding="utf-8")
            print(f"✏️ [替换] {path}")
            return f"替换完成 ({len(replaced.encode('utf-8'))} 字节)"

        elif action == "insert":
            line = int(input_obj.get("insert_after", -1))
            lines = text.split("\n")
            idx = max(-1, min(len(lines) - 1, line))
            lines[idx + 1:idx + 1] = [str(input_obj.get("new_text", ""))]
            fp.write_text("\n".join(lines), encoding="utf-8")
            print(f"➕ [插入] {path} (第 {line} 行后)")
            return f"已在第 {line} 行后插入"

        elif action == "delete_range":
            rng = input_obj.get("range", [])
            if len(rng) != 2 or rng[1] < rng[0]:
                return "错误: 无效的 range 参数"
            s, e = rng
            lines = text.split("\n")
            fp.write_text("\n".join([*lines[:s], *lines[e:]]), encoding="utf-8")
            print(f"❌ [删除] {path} (行 {s}-{e})")
            return f"已删除行 [{s}, {e})"

        else:
            return f"错误: 不支持的 action: {action}"

    except Exception as e:
        return f"错误: {e}"


def _tool_goto_location(input_obj: dict, npc, context) -> str:
    """
    前往指定地点 (调用者自己去)

    Args:
        input_obj: {"location": "酒馆"}
        npc: 调用者 (谁调用谁去)
        context: 上下文

    Returns:
        str: 执行结果
    """
    location_name = input_obj.get("location", "")

    if not location_name:
        return "错误: 缺少 location 参数"

    # 查地点注册表
    from env import map as map_module
    coords = map_module.get_location_coords(location_name)

    if not coords:
        return f"错误: 未找到地点 '{location_name}'"

    target_x, target_y = coords

    # 设置调用者的移动目标
    npc.walk_mode = WalkMode.TO_TARGET
    npc.walk_target = (target_x, target_y)
    npc.walk_target_name = location_name  # 记录目标地点名称
    npc.walk_mode_tick = 0

    print(f"🎯 [Goto] {npc.name} 前往 {location_name} ({target_x}, {target_y})")
    return f"开始前往 {location_name}"


def _tool_arrived_at(input_obj: dict, npc, context) -> str:
    """
    确认已到达指定地点

    Args:
        input_obj: {"location": "酒馆"}
        npc: 调用者
        context: 上下文

    Returns:
        str: 执行结果
    """
    location_name = input_obj.get("location", "")

    if not location_name:
        return "错误: 缺少 location 参数"

    # 清除移动目标状态
    npc.walk_mode = WalkMode.IDLE
    npc.walk_target = None
    npc.walk_target_name = None
    npc.walk_mode_tick = 0

    print(f"✅ [Arrived] {npc.name} 确认到达 {location_name}")
    return f"已到达 {location_name}"


def _tool_end_conversation(input_obj: dict, npc, context) -> str:
    """NPC 主动结束对话 (微信/其他对话均可)"""
    farewell = input_obj.get("farewell", "再见~")
    npc.memory['_end_conversation'] = farewell
    print(f"👋 [EndConv] {npc.name} 主动结束对话: {farewell}")
    return f"对话即将结束，告别语: {farewell}"


def _tool_edit_memory_note(input_obj: dict, npc, context) -> str:
    """
    编辑 NPC 的个人笔记

    Args:
        input_obj: {"content": "笔记内容", "mode": "set" | "append"}
        npc: 调用者
        context: 上下文

    Returns:
        str: 执行结果
    """
    content = input_obj.get("content", "")
    mode = input_obj.get("mode", "set")

    if not content:
        return "错误: 缺少 content 参数"

    if mode == "append":
        # 追加到现有笔记
        current = npc.memory.get('hdd_memory_note', '')
        if current:
            new_note = current + "\n" + content
        else:
            new_note = content
    else:
        # 覆盖写入
        new_note = content

    npc.memory['hdd_memory_note'] = new_note
    print(f"📝 [Note] {npc.name} 更新笔记 ({len(new_note)} 字符, mode={mode})")

    return f"笔记已更新 ({len(new_note)} 字符)"


def _tool_send_qq_notify(input_obj: dict, npc, context) -> str:
    """
    发送 QQ 通知

    Args:
        input_obj: {"message": "通知内容", "target": "openid (可选)"}
        npc: 调用者
        context: 上下文

    Returns:
        str: 执行结果
    """
    from tools import qq_bot

    message = input_obj.get("message", "")
    target = input_obj.get("target", None)

    if not message:
        return "错误: 缺少 message 参数"

    # 添加发送者信息
    full_message = f"[{npc.name}] {message}"

    result = qq_bot.send_notify(full_message, target)

    if result.get("success"):
        print(f"📱 [QQ] {npc.name} 发送通知: {message[:30]}...")
        return f"通知已发送: {message[:50]}..."
    else:
        return f"发送失败: {result.get('message', '未知错误')}"


# ========== 命令行工具处理函数 ==========

def _tool_run_command(input_obj: dict, npc, context) -> str:
    """执行命令行命令"""
    import subprocess
    from pathlib import Path

    command = input_obj.get("command", "").strip()
    if not command:
        return "错误: 缺少 command 参数"

    # 危险命令黑名单
    dangerous = ["rm -rf /", "format ", "del /s /q", "mkfs", "shutdown", "reboot"]
    cmd_lower = command.lower()
    for d in dangerous:
        if d in cmd_lower:
            return f"错误: 命令被拒绝 (安全限制): {d}"

    # 解析工作目录
    cwd_path = input_obj.get("cwd", "").strip()
    if cwd_path:
        resolved_cwd, err = _resolve_safe_path(cwd_path)
        if err:
            return err
        # cwd 可能指向文件，取其父目录
        work_dir = resolved_cwd if resolved_cwd.is_dir() else resolved_cwd.parent
    else:
        # 默认用项目根目录 (而非 workspace)，让 NPC 能直接访问 data/ 等目录
        work_dir = tool_module.PROJECT_ROOT or tool_module.WORKDIR or Path.cwd()

    try:
        print(f"⚙️ [命令执行] {npc.name}: {command} (cwd: {work_dir})")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(work_dir),
            shell=True,
            env={**__import__('os').environ, 'PYTHONIOENCODING': 'utf-8'},
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n--- stderr ---\n"
            output += result.stderr

        # 截断过长输出
        if len(output) > 5000:
            output = output[:5000] + f"\n...(截断, 共 {len(output)} 字符)"

        status = "成功" if result.returncode == 0 else f"失败 (exit code: {result.returncode})"
        print(f"⚙️ [命令结果] {status}")

        if not output.strip():
            return f"命令执行{status} (无输出)"
        return f"[{status}]\n{output}"

    except subprocess.TimeoutExpired:
        return "错误: 命令执行超时 (30秒)"
    except Exception as e:
        return f"错误: {e}"


# ========== 代码检查工具处理函数 ==========

def _tool_check_syntax(input_obj: dict, npc, context) -> str:
    """检查代码文件语法错误"""
    import py_compile
    import subprocess

    path = input_obj.get("path", "").strip()
    if not path:
        return "错误: 缺少 path 参数"

    resolved, err = _resolve_safe_path(path)
    if err:
        return err
    if not resolved.is_file():
        return f"错误: 文件不存在: {path}"

    ext = resolved.suffix.lower()

    # Python
    if ext == ".py":
        try:
            py_compile.compile(resolved, doraise=True)
            return f"✅ {path} 语法检查通过 (Python)"
        except py_compile.PyCompileError as e:
            return f"❌ {path} 语法错误:\n{e}"

    # JS/TS (用 node --check 或 npx tsc --noEmit)
    if ext in (".js", ".mjs", ".cjs"):
        try:
            result = subprocess.run(
                ["node", "--check", resolved],
                capture_output=True, text=True, timeout=10, shell=True,
            )
            if result.returncode == 0:
                return f"✅ {path} 语法检查通过 (JavaScript)"
            return f"❌ {path} 语法错误:\n{result.stderr.strip()}"
        except Exception as e:
            return f"检查失败: {e}"

    if ext in (".ts", ".tsx"):
        try:
            # 找 tsconfig 所在目录
            ts_dir = resolved.parent
            while ts_dir != ts_dir.parent and not (ts_dir / "tsconfig.json").is_file():
                ts_dir = ts_dir.parent

            result = subprocess.run(
                ["npx", "tsc", "--noEmit", "--pretty"],
                capture_output=True, text=True, timeout=30,
                cwd=str(ts_dir), shell=True,
            )
            if result.returncode == 0:
                return f"✅ {path} 语法检查通过 (TypeScript)"

            # 过滤只显示当前文件的错误
            filename = resolved.name
            errors = [line for line in result.stdout.split("\n") if filename in line or line.startswith(" ")]
            if errors:
                return f"❌ {path} 类型/语法错误:\n" + "\n".join(errors[:20])
            return f"✅ {path} 无错误 (但项目中其他文件可能有问题)"
        except Exception as e:
            return f"检查失败: {e}"

    return f"不支持的文件类型: {ext} (支持 .py .js .ts .tsx)"


# ========== MCP 工具处理函数 ==========

def _tool_list_mcp_servers(input_obj: dict, npc, context) -> str:
    """列出所有可用的 MCP 服务器"""
    from tools import mcp_manager

    servers = mcp_manager.list_servers()
    if not servers:
        return "当前没有注册任何 MCP 服务器。请联系管理员在前端 MCP 管理页面注册。"

    lines = ["可用的 MCP 服务器:\n"]
    for name, info in servers.items():
        status = info.get("runtime_status", "stopped")
        status_icon = "🟢 运行中" if status == "running" else "⚫ 未启动"
        desc = info.get("description", "") or f"{info.get('command', '')} {' '.join(info.get('args', []))}"
        pid = info.get("pid")
        pid_text = f" (PID: {pid})" if pid else ""

        # 检查当前 NPC 是否已连接此服务器
        connected = name in [s.get("name") for s in npc.memory.get('mcp_servers', [])]
        conn_text = " [已连接]" if connected else ""

        lines.append(f"- {name}: {status_icon}{pid_text}{conn_text}")
        lines.append(f"  描述: {desc}")

    lines.append("\n使用 connect_mcp(server_name) 连接指定服务器获取其工具。")
    return "\n".join(lines)


def _tool_connect_mcp(input_obj: dict, npc, context) -> str:
    """连接到指定的 MCP 服务器"""
    from tools import mcp_manager
    from tools.mcp_client import connect_npc_servers

    server_name = input_obj.get("server_name", "").strip()
    if not server_name:
        return "错误: 缺少 server_name 参数"

    # 检查服务器是否存在
    servers = mcp_manager.list_servers()
    if server_name not in servers:
        available = ", ".join(servers.keys()) if servers else "无"
        return f"错误: 未找到 MCP 服务器 '{server_name}'。可用: {available}"

    server_info = servers[server_name]

    # 如果服务器未运行，尝试启动
    if server_info.get("runtime_status") != "running":
        print(f"🔌 [MCP] {npc.name} 请求启动 {server_name}...")
        start_result = mcp_manager.start_server(server_name)
        if start_result.get("status") != "ok":
            return f"启动 {server_name} 失败: {start_result.get('message', '未知错误')}"
        print(f"🔌 [MCP] {server_name} 已启动")
        # 重新获取 URL
        import time
        time.sleep(1)  # 等服务器初始化

    # 获取 URL
    url = mcp_manager.get_server_url(server_name)
    if not url:
        # 尝试从配置推导
        if server_info.get("transport") == "sse" and server_info.get("port"):
            url = f"http://localhost:{server_info['port']}/sse"
        else:
            return f"错误: 无法获取 {server_name} 的连接地址 (仅支持 SSE 传输模式)"

    # 构建连接配置
    server_config = [{"name": server_name, "url": url}]

    # 合并到 NPC 的 mcp_servers (避免重复)
    existing = npc.memory.get('mcp_servers', [])
    if not any(s.get("name") == server_name for s in existing):
        existing.append({"name": server_name, "url": url})
        npc.memory['mcp_servers'] = existing

    # 连接
    try:
        tool_defs = connect_npc_servers(npc.name, server_config)
        # 合并工具定义到 NPC
        existing_defs = npc.memory.get('mcp_tool_defs', [])
        existing_names = {t.get("name") for t in existing_defs}
        for td in tool_defs:
            if td.get("name") not in existing_names:
                existing_defs.append(td)
        npc.memory['mcp_tool_defs'] = existing_defs
        npc.memory.pop('_mcp_last_fail_time', None)

        tool_names = [t.get("name", "").split("__")[-1] for t in tool_defs]
        print(f"🔌 [MCP] {npc.name} 已连接 {server_name}: {len(tool_defs)} 个工具")
        return f"已成功连接 {server_name}！获得 {len(tool_defs)} 个新工具:\n" + "\n".join(f"- {n}" for n in tool_names)
    except Exception as e:
        return f"连接 {server_name} 失败: {e}"


# ========== 背包系统工具处理函数 ==========

def _get_inventory_schema(npc) -> dict:
    """获取 NPC 的背包 schema"""
    return npc.memory.get('inventory_schema', {})


def _get_inventory(npc) -> dict:
    """获取 NPC 的背包数据"""
    return npc.memory.get('inventory', {})


def _tool_list_attrs(input_obj: dict, npc, context) -> str:
    """
    列出指定角色的所有属性 (查看别人时只显示公开属性)
    """
    target_name = input_obj.get("target", "")

    # 确定目标 NPC
    if target_name:
        target_npc = None
        npcs_ref = context.get('npcs', [])
        for n in npcs_ref:
            if n.name.lower() == target_name.lower():
                target_npc = n
                break
        if not target_npc:
            return f"错误: 未找到 NPC '{target_name}'"
    else:
        target_npc = npc

    is_self = (target_npc == npc)
    schema = _get_inventory_schema(target_npc)
    inventory = _get_inventory(target_npc)
    result_lines = []

    for attr_name, attr_config in schema.items():
        visibility = attr_config.get('visibility', 'private')
        # 查看别人时只显示 public 属性
        if not is_self and visibility == 'private':
            continue
        value = inventory.get(attr_name, "<未设置>")
        desc = attr_config.get('description', '')
        line = f"- {attr_name} = {value}"
        if desc:
            line += f" ({desc})"
        if is_self and visibility == 'private':
            line += " [私有]"
        result_lines.append(line)

    if not result_lines:
        who = target_npc.name if not is_self else "你"
        return f"{who}没有可查看的属性"

    header = f"{target_npc.name}的属性:" if not is_self else "你的属性:"
    return header + "\n" + "\n".join(result_lines)


def _tool_get_auth_code(input_obj: dict, npc, context) -> str:
    """
    获取某属性的授权码 (用于修改敏感属性)
    """
    import uuid

    attr = input_obj.get("attr", "")
    if not attr:
        return "错误: 缺少 attr 参数"

    schema = _get_inventory_schema(npc)
    if attr not in schema:
        return f"错误: 属性 '{attr}' 不存在"

    attr_config = schema[attr]
    if not attr_config.get('requires_auth', False):
        return f"属性 '{attr}' 不需要授权码，可以直接修改"

    if not attr_config.get('writable_by_owner', False):
        return f"错误: 属性 '{attr}' 你没有修改权限"

    # 生成一次性授权码
    auth_code = str(uuid.uuid4())[:8]

    # 存储授权码 (在 memory 中)
    if 'inventory_auth_codes' not in npc.memory:
        npc.memory['inventory_auth_codes'] = {}
    npc.memory['inventory_auth_codes'][attr] = auth_code

    print(f"🔐 [Auth] {npc.name} 获取属性 '{attr}' 的授权码: {auth_code}")
    return f"授权码: {auth_code} (只能使用一次，请妥善保管)"


def _tool_read_attr(input_obj: dict, npc, context) -> str:
    """
    读取属性值

    权限规则:
    - visibility: public -> 任何人可读
    - visibility: private -> 仅自己可读
    """
    target_name = input_obj.get("target", "")
    attr = input_obj.get("attr", "")

    if not attr:
        return "错误: 缺少 attr 参数"

    # 确定目标 NPC
    if target_name:
        # 读取别人的属性
        target_npc = None
        npcs_ref = context.get('npcs', [])
        for n in npcs_ref:
            if n.name.lower() == target_name.lower():
                target_npc = n
                break

        if not target_npc:
            return f"错误: 未找到 NPC '{target_name}'"

        schema = _get_inventory_schema(target_npc)
        inventory = _get_inventory(target_npc)
    else:
        # 读取自己的属性
        target_npc = npc
        schema = _get_inventory_schema(npc)
        inventory = _get_inventory(npc)

    if attr not in schema:
        return f"错误: 属性 '{attr}' 不存在"

    attr_config = schema[attr]
    visibility = attr_config.get('visibility', 'private')

    # 权限检查
    if visibility == 'private' and target_npc != npc:
        return f"错误: 属性 '{attr}' 是私有的，无法读取"

    # 返回属性值
    value = inventory.get(attr, "<未设置>")
    print(f"📖 [ReadAttr] {npc.name} 读取 {target_npc.name} 的 '{attr}': {value}")
    return f"{attr} = {value}"


def _tool_edit_attr(input_obj: dict, npc, context) -> str:
    """
    设置属性的数值和描述
    """
    attr = input_obj.get("attr", "")
    value = input_obj.get("value")
    description = input_obj.get("description", "")
    auth_code = input_obj.get("auth_code", "")
    target_name = input_obj.get("target", "")

    if not attr:
        return "错误: 缺少 attr 参数"
    if value is None:
        return "错误: 缺少 value 参数"

    # 强制转换为数字
    try:
        num_value = float(value)
        if num_value == int(num_value):
            value = str(int(num_value))
        else:
            value = str(num_value)
    except (ValueError, TypeError):
        return f"错误: value 必须是数字，你传入的是 '{value}'"

    # 确定目标 NPC
    target_npc = npc
    if target_name:
        # 查找目标 NPC
        npcs = context.get('npcs', [])
        for n in npcs:
            if n.name.lower() == target_name.lower():
                target_npc = n
                break
        if target_npc == npc and target_name.lower() != npc.name.lower():
            return f"错误: 未找到 NPC '{target_name}'"

    schema = _get_inventory_schema(target_npc)

    is_new_attr = attr not in schema
    if is_new_attr:
        # 新建属性：visibility 由调用者指定，默认 public
        vis = input_obj.get("visibility", "public")
        if vis not in ("public", "private"):
            vis = "public"
        schema[attr] = {
            'visibility': vis,
            'writable_by_owner': True,
            'writable_by_others': True,
            'requires_auth': False,
            'description': ''
        }
        target_npc.memory['inventory_schema'] = schema

    attr_config = schema[attr]

    # 新建属性跳过权限检查，已有属性才检查
    if not is_new_attr:
        if target_npc == npc:
            if not attr_config.get('writable_by_owner', False):
                return f"错误: 属性 '{attr}' 你没有修改权限"
        else:
            if not attr_config.get('writable_by_others', False):
                return f"错误: 属性 '{attr}' 不允许他人修改"

    # 检查是否需要授权码
    if attr_config.get('requires_auth', False):
        stored_code = target_npc.memory.get('inventory_auth_codes', {}).get(attr)
        if not auth_code:
            return f"错误: 属性 '{attr}' 需要授权码，请先使用 get_auth_code 获取"
        if auth_code != stored_code:
            return f"错误: 授权码无效"
        # 授权码使用后删除
        del target_npc.memory['inventory_auth_codes'][attr]

    # 更新属性值
    inventory = _get_inventory(target_npc)
    inventory[attr] = value
    target_npc.memory['inventory'] = inventory

    # 更新描述（如果提供了）
    if description:
        schema[attr]['description'] = description
        target_npc.memory['inventory_schema'] = schema

    target_info = f"({target_npc.name}) " if target_npc != npc else ""
    print(f"✏️ [EditAttr] {npc.name} 设置 {target_info}'{attr}' = {value}" + (f", 描述: {description[:20]}..." if description else ""))
    return f"已设置 {attr} = {value}" + (f"，描述已更新" if description else "")


def _tool_modify_attr(input_obj: dict, npc, context) -> str:
    """
    增减数值型属性
    """
    attr = input_obj.get("attr", "")
    delta = input_obj.get("delta", 0)
    auth_code = input_obj.get("auth_code", "")
    target_name = input_obj.get("target", "")

    if not attr:
        return "错误: 缺少 attr 参数"

    # 确定目标 NPC
    target_npc = npc
    if target_name:
        npcs = context.get('npcs', [])
        for n in npcs:
            if n.name.lower() == target_name.lower():
                target_npc = n
                break
        if target_npc == npc and target_name.lower() != npc.name.lower():
            return f"错误: 未找到 NPC '{target_name}'"

    schema = _get_inventory_schema(target_npc)
    inventory = _get_inventory(target_npc)

    if attr not in schema:
        return f"错误: 属性 '{attr}' 不存在"

    attr_config = schema[attr]

    # 检查是否可写
    if target_npc == npc:
        if not attr_config.get('writable_by_owner', False):
            return f"错误: 属性 '{attr}' 你没有修改权限"
    else:
        if not attr_config.get('writable_by_others', False):
            return f"错误: 属性 '{attr}' 不允许他人修改"

    # 检查是否需要授权码
    if attr_config.get('requires_auth', False):
        stored_code = target_npc.memory.get('inventory_auth_codes', {}).get(attr)
        if not auth_code:
            return f"错误: 属性 '{attr}' 需要授权码，请先使用 get_auth_code 获取"
        if auth_code != stored_code:
            return f"错误: 授权码无效"
        del target_npc.memory['inventory_auth_codes'][attr]

    # 获取当前值并尝试转为数值
    current_value = inventory.get(attr, 0)
    try:
        current_num = float(current_value)
    except (ValueError, TypeError):
        return f"错误: 属性 '{attr}' 当前值 '{current_value}' 不是数值，无法增减"

    # 计算新值
    new_num = current_num + delta
    # 如果是整数则保持整数
    if isinstance(current_num, int) or current_num == int(current_num):
        new_value = str(int(new_num))
    else:
        new_value = str(new_num)

    inventory[attr] = new_value
    target_npc.memory['inventory'] = inventory

    sign = "+" if delta >= 0 else ""
    target_info = f"({target_npc.name}) " if target_npc != npc else ""
    print(f"🔢 [ModifyAttr] {npc.name} 修改 {target_info}'{attr}': {current_value} {sign}{delta} = {new_value}")
    return f"{attr}: {current_value} → {new_value} ({sign}{delta})"


def _tool_delete_attr(input_obj: dict, npc, context) -> str:
    """
    删除属性/物品
    """
    attr = input_obj.get("attr", "")
    auth_code = input_obj.get("auth_code", "")
    target_name = input_obj.get("target", "")

    if not attr:
        return "错误: 缺少 attr 参数"

    # 确定目标 NPC
    target_npc = npc
    if target_name:
        npcs = context.get('npcs', [])
        for n in npcs:
            if n.name.lower() == target_name.lower():
                target_npc = n
                break
        if target_npc == npc and target_name.lower() != npc.name.lower():
            return f"错误: 未找到 NPC '{target_name}'"

    schema = _get_inventory_schema(target_npc)
    inventory = _get_inventory(target_npc)

    # 检查属性是否存在 (schema 或 inventory 中有任意一个就算存在)
    if attr not in schema and attr not in inventory:
        return f"错误: 属性 '{attr}' 不存在"

    attr_config = schema.get(attr, {})

    # 检查是否可写
    if target_npc == npc:
        if not attr_config.get('writable_by_owner', False):
            return f"错误: 属性 '{attr}' 你没有删除权限"
    else:
        if not attr_config.get('writable_by_others', False):
            return f"错误: 属性 '{attr}' 不允许他人删除"

    # 检查是否需要授权码
    if attr_config.get('requires_auth', False):
        stored_code = target_npc.memory.get('inventory_auth_codes', {}).get(attr)
        if not auth_code:
            return f"错误: 属性 '{attr}' 需要授权码，请先使用 get_auth_code 获取"
        if auth_code != stored_code:
            return f"错误: 授权码无效"
        del target_npc.memory['inventory_auth_codes'][attr]

    # 删除 inventory 中的值
    old_value = inventory.pop(attr, None)

    # 删除 schema 中的定义
    if attr in schema:
        del schema[attr]
        target_npc.memory['inventory_schema'] = schema

    target_npc.memory['inventory'] = inventory

    target_info = f"({target_npc.name}) " if target_npc != npc else ""
    print(f"🗑️ [DeleteAttr] {npc.name} 删除 {target_info}'{attr}' (原值: {old_value})")
    return f"已删除 {attr}"


# ========== 主动性工具处理函数 ==========

def _tool_modify_initiative(input_obj: dict, npc, context) -> str:
    """
    调整自己的主动性

    Args:
        input_obj: {"delta": 2, "reason": "聊得很开心"}
        npc: 调用者
        context: 上下文

    Returns:
        str: 执行结果
    """
    delta = input_obj.get("delta", 0)
    reason = input_obj.get("reason", "")

    if delta == 0:
        return "主动性未变化 (delta=0)"

    # 获取当前值
    old_value = npc.initiative

    # 计算新值并应用边界限制 (-10 到 10)
    new_value = max(-10, min(10, old_value + delta))
    npc.initiative = new_value

    # 记录日志
    sign = "+" if delta >= 0 else ""
    reason_text = f" ({reason})" if reason else ""
    print(f"💪 [Initiative] {npc.name}: {old_value} -> {new_value} ({sign}{delta}){reason_text}")

    return f"主动性: {old_value} → {new_value} ({sign}{delta}){reason_text}"


def _tool_modify_others_initiative(input_obj: dict, npc, context) -> str:
    """
    调整他人的主动性

    Args:
        input_obj: {"target": "Bob", "delta": -2, "reason": "话题无聊"}
        npc: 调用者
        context: 上下文 (需要包含 npcs 列表)

    Returns:
        str: 执行结果
    """
    target_name = input_obj.get("target", "")
    delta = input_obj.get("delta", 0)
    reason = input_obj.get("reason", "")

    if not target_name:
        return "错误: 缺少 target 参数"

    if delta == 0:
        return f"{target_name} 的主动性未变化 (delta=0)"

    # 查找目标 NPC
    target_npc = None
    npcs_ref = context.get('npcs', [])
    for n in npcs_ref:
        if n.name.lower() == target_name.lower():
            target_npc = n
            break

    if not target_npc:
        return f"错误: 未找到 NPC '{target_name}'"

    # 不能调整自己的主动性 (应该用 modify_initiative)
    if target_npc == npc:
        return "错误: 请使用 modify_initiative 调整自己的主动性"

    # 获取当前值
    old_value = target_npc.initiative

    # 计算新值并应用边界限制 (-10 到 10)
    new_value = max(-10, min(10, old_value + delta))
    target_npc.initiative = new_value

    # 记录日志
    sign = "+" if delta >= 0 else ""
    reason_text = f" ({reason})" if reason else ""
    print(f"💪 [Initiative] {npc.name} 影响 {target_npc.name}: {old_value} -> {new_value} ({sign}{delta}){reason_text}")

    return f"{target_npc.name} 的主动性: {old_value} → {new_value} ({sign}{delta}){reason_text}"


# ========== 初始化 ==========

def _init_handlers():
    """初始化工具处理函数映射"""
    # Custom 协议
    tool_module.TOOL_REGISTRY["custom"][1]["handler"] = _tool_1_test
    tool_module.TOOL_REGISTRY["custom"][2]["handler"] = _tool_2_add_group

    # Anthropic 协议
    tool_module.TOOL_REGISTRY["anthropic"]["read_file"]["handler"] = _tool_read_file
    tool_module.TOOL_REGISTRY["anthropic"]["write_file"]["handler"] = _tool_write_file
    tool_module.TOOL_REGISTRY["anthropic"]["delete_file"]["handler"] = _tool_delete_file
    tool_module.TOOL_REGISTRY["anthropic"]["edit_text"]["handler"] = _tool_edit_text
    tool_module.TOOL_REGISTRY["anthropic"]["goto_location"]["handler"] = _tool_goto_location
    tool_module.TOOL_REGISTRY["anthropic"]["arrived_at"]["handler"] = _tool_arrived_at
    tool_module.TOOL_REGISTRY["anthropic"]["end_conversation"]["handler"] = _tool_end_conversation
    tool_module.TOOL_REGISTRY["anthropic"]["edit_memory_note"]["handler"] = _tool_edit_memory_note
    tool_module.TOOL_REGISTRY["anthropic"]["send_qq_notify"]["handler"] = _tool_send_qq_notify

    # 命令行 & 代码检查工具
    tool_module.TOOL_REGISTRY["anthropic"]["run_command"]["handler"] = _tool_run_command
    tool_module.TOOL_REGISTRY["anthropic"]["check_syntax"]["handler"] = _tool_check_syntax

    # MCP 工具
    tool_module.TOOL_REGISTRY["anthropic"]["list_mcp_servers"]["handler"] = _tool_list_mcp_servers
    tool_module.TOOL_REGISTRY["anthropic"]["connect_mcp"]["handler"] = _tool_connect_mcp

    # 背包系统工具
    tool_module.TOOL_REGISTRY["anthropic"]["list_attrs"]["handler"] = _tool_list_attrs
    tool_module.TOOL_REGISTRY["anthropic"]["get_auth_code"]["handler"] = _tool_get_auth_code
    tool_module.TOOL_REGISTRY["anthropic"]["read_attr"]["handler"] = _tool_read_attr
    tool_module.TOOL_REGISTRY["anthropic"]["edit_attr"]["handler"] = _tool_edit_attr
    tool_module.TOOL_REGISTRY["anthropic"]["modify_attr"]["handler"] = _tool_modify_attr
    tool_module.TOOL_REGISTRY["anthropic"]["delete_attr"]["handler"] = _tool_delete_attr

    # 任务工具 (从 task_l1 导入，避免循环依赖)
    from tools.task_l1 import _tool_add_task, _tool_complete_task
    tool_module.TOOL_REGISTRY["anthropic"]["add_task"]["handler"] = _tool_add_task
    tool_module.TOOL_REGISTRY["anthropic"]["complete_task"]["handler"] = _tool_complete_task

    # 定时器工具 (从 timer_l1 导入)
    from tools.timer_l1 import _tool_create_timer, _tool_remove_timer, _tool_list_timers
    tool_module.TOOL_REGISTRY["anthropic"]["create_timer"]["handler"] = _tool_create_timer
    tool_module.TOOL_REGISTRY["anthropic"]["remove_timer"]["handler"] = _tool_remove_timer
    tool_module.TOOL_REGISTRY["anthropic"]["list_timers"]["handler"] = _tool_list_timers

    # 主动性工具
    tool_module.TOOL_REGISTRY["anthropic"]["modify_initiative"]["handler"] = _tool_modify_initiative
    tool_module.TOOL_REGISTRY["anthropic"]["modify_others_initiative"]["handler"] = _tool_modify_others_initiative

    # 邮箱工具 (从 mailbox_l1 导入)
    from tools.mailbox_l1 import _tool_send_mail, _tool_send_image_mail, _tool_send_html_mail
    tool_module.TOOL_REGISTRY["anthropic"]["send_mail"]["handler"] = _tool_send_mail
    tool_module.TOOL_REGISTRY["anthropic"]["send_image_mail"]["handler"] = _tool_send_image_mail
    tool_module.TOOL_REGISTRY["anthropic"]["send_html_mail"]["handler"] = _tool_send_html_mail

    # 内置浏览器工具 (从 browser_l1 导入)
    from tools.browser_l1 import (
        tool_browser_open, tool_browser_click, tool_browser_type,
        tool_browser_screenshot, tool_browser_snapshot, tool_browser_close
    )
    tool_module.TOOL_REGISTRY["anthropic"]["browser_open"]["handler"] = tool_browser_open
    tool_module.TOOL_REGISTRY["anthropic"]["browser_click"]["handler"] = tool_browser_click
    tool_module.TOOL_REGISTRY["anthropic"]["browser_type"]["handler"] = tool_browser_type
    tool_module.TOOL_REGISTRY["anthropic"]["browser_screenshot"]["handler"] = tool_browser_screenshot
    tool_module.TOOL_REGISTRY["anthropic"]["browser_snapshot"]["handler"] = tool_browser_snapshot
    tool_module.TOOL_REGISTRY["anthropic"]["browser_close"]["handler"] = tool_browser_close

    # 人机交互工具 (从 form_l1 导入)
    from tools.form_l1 import _tool_ask_human
    tool_module.TOOL_REGISTRY["anthropic"]["ask_human"]["handler"] = _tool_ask_human

    # NPC 协作工具 (从 npc_tools_l1 导入)
    from tools.npc_tools_l1 import _tool_invoke_npc, _tool_create_npc
    tool_module.TOOL_REGISTRY["anthropic"]["invoke_npc"]["handler"] = _tool_invoke_npc
    tool_module.TOOL_REGISTRY["anthropic"]["create_npc"]["handler"] = _tool_create_npc

    # 知识库检索工具 (从 knowledge_l1 导入)
    from tools.knowledge_l1 import _tool_search_knowledge
    tool_module.TOOL_REGISTRY["anthropic"]["search_knowledge"]["handler"] = _tool_search_knowledge

    # 图片生成/编辑工具 (从 image_l1 导入)
    from tools.image_l1 import _tool_image_generate, _tool_image_edit
    tool_module.TOOL_REGISTRY["anthropic"]["image_generate"]["handler"] = _tool_image_generate
    tool_module.TOOL_REGISTRY["anthropic"]["image_edit"]["handler"] = _tool_image_edit

    # 漫画排版工具 (从 composite_l1 导入)
    from tools.composite_l1 import _tool_composite_image
    tool_module.TOOL_REGISTRY["anthropic"]["composite_image"]["handler"] = _tool_composite_image

    # TTS 语音合成工具 (从 tts_l1 导入)
    from tools.tts_l1 import _tool_tts
    tool_module.TOOL_REGISTRY["anthropic"]["tts"]["handler"] = _tool_tts

    # ASR 语音识别工具 (从 asr_l1 导入)
    from tools.asr_l1 import _tool_asr
    tool_module.TOOL_REGISTRY["anthropic"]["asr"]["handler"] = _tool_asr

    # 图转视频工具 (从 i2v_l1 导入)
    from tools.i2v_l1 import _tool_image_to_video
    tool_module.TOOL_REGISTRY["anthropic"]["image_to_video"]["handler"] = _tool_image_to_video

    # 视频合成工具 (从 video_l1 导入)
    from tools.video_l1 import _tool_make_video
    tool_module.TOOL_REGISTRY["anthropic"]["make_video"]["handler"] = _tool_make_video


_init_handlers()


# ========== 执行接口 ==========

def invoke_custom_sync(npc, response_text, listener=None):
    """同步检测并调用自定义协议工具"""
    from tools.tool_providers.providers import get_provider

    provider = get_provider("custom")
    tools = list(tool_module.TOOL_REGISTRY.get("custom", {}).items())
    tools_list = [
        {"tool_id": tid, **t}
        for tid, t in tools
        if t.get("enabled", True) and t.get("trigger") and t.get("handler")
    ]

    context = {"response": response_text, "listener": listener}
    detected = provider.detect_trigger(response_text, tools_list)

    results = []
    for tool_call in detected:
        handler = None
        for tid, t in tool_module.TOOL_REGISTRY.get("custom", {}).items():
            if t.get("name") == tool_call.get("name"):
                handler = t.get("handler")
                break

        if handler:
            try:
                result = provider.execute(tool_call, handler, npc, context)
                results.append({
                    "tool_id": tool_call.get("tool_id"),
                    "tool_name": tool_call.get("name"),
                    "success": True,
                    "result": result,
                })
                print(f"[Tool:Custom] 触发: {tool_call.get('name')}")
            except Exception as e:
                results.append({
                    "tool_id": tool_call.get("tool_id"),
                    "tool_name": tool_call.get("name"),
                    "success": False,
                    "error": str(e),
                })

    return results


def invoke_custom_async(npc, response_text, listener=None, callback=None):
    """异步检测并调用自定义协议工具"""
    thread = threading.Thread(
        target=_invoke_custom_thread,
        args=(npc, response_text, listener, callback),
        daemon=True
    )
    thread.start()
    return thread


def _invoke_custom_thread(npc, response_text, listener, callback):
    """自定义协议异步调用线程"""
    results = invoke_custom_sync(npc, response_text, listener)
    if callback and results:
        callback(npc, results)


# 兼容旧接口
invoke_async = invoke_custom_async


# ========== 协议路由 ==========

def detect_and_invoke(npc, text, registry, context):
    """
    检测文本中的工具触发模式并调用 (兼容旧接口)

    Args:
        npc: NPC对象
        text: AI回复文本
        registry: 工具注册表 (custom 协议)
        context: 上下文字典

    Returns:
        list: 调用结果列表
    """
    return invoke_custom_sync(npc, text, context.get("listener"))


def invoke_anthropic_tools(npc, response, context: Dict) -> List[Dict]:
    """
    处理 Anthropic 原生工具调用

    Args:
        npc: NPC 对象
        response: Anthropic API 响应
        context: 上下文 {"listener": ...}

    Returns:
        工具执行结果列表
    """
    from tools.tool_providers.providers import get_provider

    provider = get_provider("anthropic")
    tools = list(tool_module.TOOL_REGISTRY.get("anthropic", {}).values())
    tools_list = [t for t in tools if t.get("enabled", True) and t.get("handler")]

    detected = provider.detect_trigger(response, tools_list)
    results = []

    for tool_call in detected:
        tool_name = tool_call.get("name")
        handler = tool_module.TOOL_REGISTRY.get("anthropic", {}).get(tool_name, {}).get("handler")

        if handler:
            try:
                result = provider.execute(tool_call, handler, npc, context)
                tool_result = provider.format_result(tool_call, result)
                results.append({
                    "tool_name": tool_name,
                    "success": True,
                    "result": result,
                    "tool_result": tool_result,  # 用于返回给 LLM
                })
                print(f"[Tool:Anthropic] 执行: {tool_name}")
            except Exception as e:
                results.append({
                    "tool_name": tool_name,
                    "success": False,
                    "error": str(e),
                })

    return results
