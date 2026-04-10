# ============================================
# tools/mcp_client.py - MCP客户端总控层
# 职责: 配置持有、异步桥接、持久会话管理 (懒加载)
# ============================================

import asyncio
import threading
import time
from tools.mcp_client_l1 import PersistentMCPSession

# ========== 异步事件循环 (桥接同步主循环) ==========
_loop = None
_thread = None

# 持久会话: {npc_name: {server_name: PersistentMCPSession}}
_sessions = {}

# 待连接配置: {npc_name: [{"name": ..., "url": ...}]}
_pending_configs = {}

# MCP Server 配置缓存: {npc_name: {server_name: url}}
_server_configs = {}

# MCP 工具定义缓存: {npc_name: [tool_defs]}
_tool_defs_cache = {}


def init():
    """启动专用 asyncio 事件循环线程"""
    global _loop, _thread
    if _loop is not None:
        return

    _loop = asyncio.new_event_loop()
    _thread = threading.Thread(target=_loop.run_forever, daemon=True, name="mcp-event-loop")
    _thread.start()
    print("[MCP] 异步事件循环已启动")


def _run_async(coro, timeout=60):
    """同步调用异步协程的桥接"""
    if _loop is None:
        init()
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=timeout)


def register_pending_servers(npc_name, server_configs):
    """注册 MCP Server 配置，不立即连接 (懒加载)

    返回占位工具定义，让 NPC 的 prompt 里能看到有 MCP 工具可用。
    实际连接在第一次调用 call_tool 时触发。

    Args:
        npc_name: NPC 名称
        server_configs: [{"url": "http://...", "name": "weather"}, ...]

    Returns:
        list: 占位工具定义 (基本信息，无详细 schema)
    """
    _pending_configs[npc_name] = server_configs

    # 记录 server 配置
    npc_servers = {}
    for config in server_configs:
        url = config.get("url", "")
        name = config.get("name", "unknown")
        if url:
            npc_servers[name] = url
    _server_configs[npc_name] = npc_servers

    mcp_count = len(npc_servers)
    if mcp_count > 0:
        print(f"[MCP] {npc_name} 注册 {mcp_count} 个 MCP Server (懒加载，首次调用时连接)")

    # 返回空列表 - 工具定义在首次连接时才获取
    return []


def _ensure_connected(npc_name, server_name):
    """确保指定的 MCP Server 已连接，未连接则立即连接

    Returns:
        PersistentMCPSession or None
    """
    npc_sessions = _sessions.get(npc_name, {})
    session = npc_sessions.get(server_name)

    if session and session.is_connected:
        return session

    # 需要连接
    url = _server_configs.get(npc_name, {}).get(server_name)
    if not url:
        return None

    print(f"[MCP] {npc_name} 首次调用 {server_name}，建立持久连接...")
    last_err = None
    for attempt in range(3):
        try:
            session = PersistentMCPSession(url, server_name)
            tool_defs = _run_async(session.connect())
            # 更新会话和缓存
            if npc_name not in _sessions:
                _sessions[npc_name] = {}
            _sessions[npc_name][server_name] = session
            # 更新工具定义缓存
            existing = _tool_defs_cache.get(npc_name, [])
            existing.extend(tool_defs)
            _tool_defs_cache[npc_name] = existing
            print(f"[MCP] {npc_name} <- {server_name}: {len(tool_defs)} 个工具 (持久会话)")
            return session
        except Exception as e:
            last_err = e
            if attempt < 2:
                print(f"[MCP] {server_name} 连接失败 (尝试 {attempt+1}/3)，2秒后重试...")
                time.sleep(2)

    print(f"[MCP] WARNING {npc_name} 连接 {server_name} 失败: {last_err}")
    return None


def connect_npc_servers(npc_name, server_configs):
    """立即连接 NPC 的所有 MCP Server (用于前端手动触发)

    Args:
        npc_name: NPC 名称
        server_configs: [{"url": "http://...", "name": "weather"}, ...]

    Returns:
        list: Anthropic 格式的工具定义
    """
    all_tool_defs = []
    npc_servers = {}
    npc_sessions = {}

    for config in server_configs:
        url = config.get("url", "")
        name = config.get("name", "unknown")
        if not url:
            continue

        try:
            print(f"[MCP] {npc_name} 连接 {name} ({url})...")
            last_err = None
            for attempt in range(3):
                try:
                    session = PersistentMCPSession(url, name)
                    tool_defs = _run_async(session.connect())
                    all_tool_defs.extend(tool_defs)
                    npc_servers[name] = url
                    npc_sessions[name] = session
                    print(f"[MCP] {npc_name} <- {name}: {len(tool_defs)} 个工具 (持久会话)")
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    if attempt < 2:
                        print(f"[MCP] {name} 连接失败 (尝试 {attempt+1}/3)，2秒后重试...")
                        time.sleep(2)
            if last_err:
                raise last_err
        except Exception as e:
            print(f"[MCP] WARNING {npc_name} 连接 {name} 失败: {e}")

    # 先关闭旧的会话
    _close_npc_sessions(npc_name)

    _server_configs[npc_name] = npc_servers
    _tool_defs_cache[npc_name] = all_tool_defs
    _sessions[npc_name] = npc_sessions
    # 清除 pending（已经连接了）
    _pending_configs.pop(npc_name, None)
    return all_tool_defs


def call_tool(npc_name, server_name, tool_name, arguments):
    """在持久会话上执行 MCP 工具 (按需连接)

    Args:
        npc_name: 调用者 NPC 名称
        server_name: MCP Server 名称
        tool_name: 工具名 (不含 mcp__ 前缀)
        arguments: 参数 dict

    Returns:
        str: 执行结果文本
    """
    session = _ensure_connected(npc_name, server_name)
    if not session:
        return f"错误: MCP Server '{server_name}' 未连接且无法连接"

    try:
        print(f"[MCP] {npc_name} 调用 {server_name}/{tool_name}")
        result = _run_async(session.call_tool(tool_name, arguments))
        print(f"[MCP] {server_name}/{tool_name} 结果: {result[:80]}...")
        return result
    except Exception as e:
        return f"MCP工具执行失败: {e}"


def _close_npc_sessions(npc_name):
    """关闭 NPC 的所有持久会话"""
    old_sessions = _sessions.pop(npc_name, {})
    for name, session in old_sessions.items():
        try:
            _run_async(session.close())
        except Exception as e:
            print(f"[MCP] 关闭 {name} 会话失败: {e}")


def disconnect_npc(npc_name):
    """清理 NPC 的 MCP 会话和缓存"""
    _close_npc_sessions(npc_name)
    _server_configs.pop(npc_name, None)
    _tool_defs_cache.pop(npc_name, None)
    _pending_configs.pop(npc_name, None)


def shutdown():
    """关闭所有 MCP 持久会话和事件循环"""
    global _loop, _thread

    for npc_name in list(_sessions.keys()):
        _close_npc_sessions(npc_name)

    if _loop:
        _loop.call_soon_threadsafe(_loop.stop)
        _thread.join(timeout=5)
        _loop = None
        _thread = None
        print("[MCP] 事件循环已关闭")

    _server_configs.clear()
    _tool_defs_cache.clear()
    _sessions.clear()
    _pending_configs.clear()
