# ============================================
# tools/mcp_manager_l2.py - MCP进程管理 原子层
# 职责: 纯格式转换/校验，无状态
# ============================================

import os


def build_server_url(transport, port):
    """根据传输类型构建服务器 URL

    Args:
        transport: "stdio" | "sse"
        port: 端口号 (仅 sse 模式)

    Returns:
        str | None: URL 或 None(stdio 模式无 URL)
    """
    if transport == "sse" and port:
        return f"http://localhost:{port}/sse"
    return None


def validate_server_config(config):
    """校验服务器配置，返回 (is_valid, error_msg)"""
    if not config.get("command"):
        return False, "缺少 command 字段"
    transport = config.get("transport", "stdio")
    if transport not in ("stdio", "sse"):
        return False, f"不支持的 transport: {transport}"
    if transport == "sse" and not config.get("port"):
        return False, "SSE 模式需要指定 port"
    return True, ""


def build_status_info(name, config, process_info):
    """构建单个服务器的状态信息（供 API 返回）

    Args:
        name: 服务器名
        config: 磁盘配置
        process_info: 运行时信息 {"process": Popen, "status": str} 或 None
    """
    transport = config.get("transport", "stdio")
    port = config.get("port")
    url = build_server_url(transport, port)

    status = "stopped"
    pid = None
    if process_info:
        proc = process_info.get("process")
        if proc and proc.poll() is None:
            status = "running"
            pid = proc.pid
        else:
            status = "stopped"

    return {
        "command": config.get("command", ""),
        "args": config.get("args", []),
        "transport": transport,
        "port": port,
        "env": config.get("env", {}),
        "description": config.get("description", ""),
        "runtime_status": status,
        "pid": pid,
        "url": url,
    }
