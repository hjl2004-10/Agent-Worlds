# ============================================
# tools/mcp_manager_l1.py - MCP进程管理 业务层
# 职责: 单个进程的启停管理
# ============================================

import subprocess
import os
import sys
import time


def launch_process(command, args, env=None, cwd=None):
    """启动 MCP Server 子进程

    Args:
        command: 可执行命令 (如 "python", "npx", "node")
        args: 参数列表
        env: 额外环境变量
        cwd: 工作目录

    Returns:
        subprocess.Popen: 进程对象
    """
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    cmd = [command] + (args or [])

    # Windows 下使用 CREATE_NEW_PROCESS_GROUP 以便后续能干净地终止
    # shell=True 让 Windows 能找到 .cmd/.bat 文件 (如 npx.cmd)
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        kwargs["shell"] = True

    process = subprocess.Popen(
        cmd,
        env=full_env,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    )

    # 等一小会确认没有立即崩溃
    time.sleep(0.5)
    if process.poll() is not None:
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        raise RuntimeError(f"进程立即退出 (code={process.returncode}): {stderr[:200]}")

    return process


def terminate_process(process, timeout=5):
    """优雅终止进程

    Args:
        process: subprocess.Popen
        timeout: 等待秒数，超时后强杀
    """
    if process is None or process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def is_alive(process):
    """检查进程是否存活"""
    if process is None:
        return False
    return process.poll() is None
