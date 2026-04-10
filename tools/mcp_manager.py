# ============================================
# tools/mcp_manager.py - MCP进程管理 总控层
# 职责: 配置持有、进程生命周期管理、接口定义
# ============================================

import os
import json
import atexit
from tools import mcp_manager_l1, mcp_manager_l2

# ========== 配置 ==========
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "mcp_servers.json")
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

# 磁盘配置: {server_name: {command, args, transport, port, env, description}}
_configs = {}

# 运行时进程: {server_name: {"process": Popen}}
_processes = {}


def init():
    """加载配置文件"""
    global _configs
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            _configs = data.get("servers", {})
            print(f"[MCP Manager] 已加载 {len(_configs)} 个服务器配置")
    except Exception as e:
        print(f"[MCP Manager] 加载配置失败: {e}")
        _configs = {}

    # 注册退出清理
    atexit.register(shutdown)


def _save_config():
    """持久化配置到磁盘"""
    data = {"version": "1.0", "servers": _configs}
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_servers():
    """列出所有服务器及运行状态

    Returns:
        dict: {server_name: status_info}
    """
    result = {}
    for name, config in _configs.items():
        proc_info = _processes.get(name)
        result[name] = mcp_manager_l2.build_status_info(name, config, proc_info)
    return result


def start_server(name):
    """启动指定的 MCP Server

    Returns:
        dict: {"status": "ok"|"error", "message": str}
    """
    if name not in _configs:
        return {"status": "error", "message": f"未找到服务器配置: {name}"}

    config = _configs[name]

    # 校验
    valid, err = mcp_manager_l2.validate_server_config(config)
    if not valid:
        return {"status": "error", "message": err}

    # 检查是否已在运行
    existing = _processes.get(name)
    if existing and mcp_manager_l1.is_alive(existing.get("process")):
        return {"status": "error", "message": f"{name} 已在运行 (PID: {existing['process'].pid})"}

    # 启动
    try:
        process = mcp_manager_l1.launch_process(
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env"),
            cwd=PROJECT_ROOT,
        )
        _processes[name] = {"process": process}
        print(f"[MCP Manager] ✅ {name} 已启动 (PID: {process.pid})")
        return {"status": "ok", "message": f"{name} 已启动", "pid": process.pid}
    except Exception as e:
        print(f"[MCP Manager] ❌ {name} 启动失败: {e}")
        return {"status": "error", "message": str(e)}


def stop_server(name):
    """停止指定的 MCP Server"""
    proc_info = _processes.get(name)
    if not proc_info:
        return {"status": "error", "message": f"{name} 未在运行"}

    process = proc_info.get("process")
    if not mcp_manager_l1.is_alive(process):
        _processes.pop(name, None)
        return {"status": "ok", "message": f"{name} 已停止（进程已退出）"}

    try:
        mcp_manager_l1.terminate_process(process)
        _processes.pop(name, None)
        print(f"[MCP Manager] 🛑 {name} 已停止")
        return {"status": "ok", "message": f"{name} 已停止"}
    except Exception as e:
        return {"status": "error", "message": f"停止失败: {e}"}


def get_server_url(name):
    """获取运行中的 MCP Server 的 URL（供 NPC 连接用）

    Returns:
        str | None
    """
    config = _configs.get(name)
    if not config:
        return None

    transport = config.get("transport", "stdio")
    if transport == "sse":
        return mcp_manager_l2.build_server_url(transport, config.get("port"))

    # stdio 模式没有 URL，需要直接用进程 stdin/stdout
    return None


def create_or_update_server(name, config):
    """创建或更新服务器配置

    Args:
        name: 服务器名
        config: {"command", "args", "transport", "port", "env", "description"}
    """
    valid, err = mcp_manager_l2.validate_server_config(config)
    if not valid:
        return {"status": "error", "message": err}

    _configs[name] = config
    _save_config()
    return {"status": "ok", "message": f"服务器 {name} 配置已保存"}


def delete_server(name):
    """删除服务器配置（如果正在运行会先停止）"""
    if name in _processes:
        stop_server(name)
    if name not in _configs:
        return {"status": "error", "message": f"未找到服务器配置: {name}"}
    del _configs[name]
    _save_config()
    return {"status": "ok", "message": f"服务器 {name} 已删除"}


def shutdown():
    """停止所有运行中的服务器"""
    for name in list(_processes.keys()):
        try:
            stop_server(name)
        except Exception as e:
            print(f"[MCP Manager] 关闭 {name} 失败: {e}")
    print("[MCP Manager] 所有服务器已清理")
