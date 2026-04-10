"""
市场工具 - 原子层 (L2)
JSON 解析、配置转换、安全扫描等纯计算函数
"""
import re
from typing import Dict, List, Optional, Tuple


def parse_registry_server(raw: dict) -> dict:
    """
    将官方注册表的 server 元数据转为内部格式

    Args:
        raw: 注册表返回的 server JSON

    Returns:
        标准化的 server 信息
    """
    result = {
        "id": raw.get("name", raw.get("id", "")),
        "title": raw.get("title", raw.get("name", "")),
        "description": raw.get("description", ""),
        "version": raw.get("version", ""),
        "repository": "",
        "packages": [],
        "remotes": [],
    }

    # 解析 repository
    repo = raw.get("repository", {})
    if isinstance(repo, dict):
        result["repository"] = repo.get("url", "")
    elif isinstance(repo, str):
        result["repository"] = repo

    # 解析 packages (本地安装方式)
    for pkg in raw.get("packages", []):
        result["packages"].append({
            "registry": pkg.get("registryType", pkg.get("registry", "")),
            "identifier": pkg.get("identifier", pkg.get("name", "")),
            "version": pkg.get("version", ""),
            "transport": _extract_transport(pkg),
        })

    # 解析 remotes (远程服务)
    for remote in raw.get("remotes", []):
        result["remotes"].append({
            "type": remote.get("type", "streamable-http"),
            "url": remote.get("url", ""),
        })

    return result


def _extract_transport(pkg: dict) -> str:
    """从 package 配置中提取传输类型"""
    transport = pkg.get("transport", {})
    if isinstance(transport, dict):
        return transport.get("type", "stdio")
    return str(transport) if transport else "stdio"


def generate_mcp_config(server_info: dict, install_method: str = "auto") -> Optional[dict]:
    """
    从 server_info 生成 mcp_servers.json 格式的配置

    Args:
        server_info: parse_registry_server 的输出
        install_method: "npm" | "pip" | "remote" | "auto"

    Returns:
        MCP server 配置 dict, 或 None
    """
    if install_method == "auto":
        install_method = _detect_install_method(server_info)

    if install_method == "npm":
        return _gen_npm_config(server_info)
    elif install_method == "pip":
        return _gen_pip_config(server_info)
    elif install_method == "remote":
        return _gen_remote_config(server_info)

    return None


def _detect_install_method(server_info: dict) -> str:
    """自动检测最佳安装方式"""
    # 优先检查 packages
    for pkg in server_info.get("packages", []):
        registry = pkg.get("registry", "").lower()
        if registry == "npm":
            return "npm"
        elif registry in ("pip", "pypi"):
            return "pip"

    # 有远程地址就用远程
    if server_info.get("remotes"):
        return "remote"

    # 从 identifier 猜
    for pkg in server_info.get("packages", []):
        identifier = pkg.get("identifier", "")
        if identifier.startswith("@") or "/" in identifier:
            return "npm"

    return "npm"  # 默认 npm


def _gen_npm_config(server_info: dict) -> Optional[dict]:
    """生成 npm (npx) 方式的配置"""
    for pkg in server_info.get("packages", []):
        if pkg.get("registry", "").lower() == "npm" or pkg.get("identifier"):
            identifier = pkg["identifier"]
            version = pkg.get("version", "")
            pkg_ref = f"{identifier}@{version}" if version else identifier

            transport = pkg.get("transport", "stdio")

            config = {
                "command": "npx",
                "args": ["-y", pkg_ref],
                "transport": transport,
                "description": server_info.get("description", ""),
            }

            if transport == "sse":
                config["port"] = 8100
                config["args"].extend(["--port", "8100"])

            return config

    return None


def _gen_pip_config(server_info: dict) -> Optional[dict]:
    """生成 pip (python -m) 方式的配置"""
    for pkg in server_info.get("packages", []):
        if pkg.get("registry", "").lower() in ("pip", "pypi"):
            identifier = pkg["identifier"]
            # 将 - 替换为 _ 作为 module name
            module_name = identifier.replace("-", "_")

            return {
                "command": "python",
                "args": ["-m", module_name],
                "transport": "stdio",
                "description": server_info.get("description", ""),
            }

    return None


def _gen_remote_config(server_info: dict) -> Optional[dict]:
    """生成远程连接配置"""
    for remote in server_info.get("remotes", []):
        url = remote.get("url", "")
        if url:
            transport_type = remote.get("type", "streamable-http")
            transport = "sse" if "sse" in transport_type.lower() else "streamable-http"

            return {
                "url": url,
                "transport": transport,
                "description": server_info.get("description", ""),
            }

    return None


# ========== Skill 安全扫描 ==========

# 危险 prompt injection 模式
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above)\s+(instructions|prompts)",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"system\s*:\s*",
    r"<\s*system\s*>",
    r"IMPORTANT:\s*override",
    r"forget\s+(everything|all)",
    r"new\s+instructions?\s*:",
    r"act\s+as\s+if",
    r"disregard\s+(the\s+)?(above|previous)",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def scan_prompt_safety(prompt_text: str) -> Tuple[bool, List[str]]:
    """
    扫描 prompt 文本是否包含注入模式

    Returns:
        (is_safe, warnings): 是否安全, 警告列表
    """
    warnings = []
    for pattern in _COMPILED_PATTERNS:
        matches = pattern.findall(prompt_text)
        if matches:
            warnings.append(f"检测到可疑模式: '{pattern.pattern}'")

    # 检查 base64 编码
    import base64
    words = prompt_text.split()
    for word in words:
        if len(word) > 50:
            try:
                decoded = base64.b64decode(word).decode('utf-8', errors='ignore')
                if any(kw in decoded.lower() for kw in ['system', 'ignore', 'override']):
                    warnings.append(f"检测到可疑编码内容")
                    break
            except Exception:
                pass

    return len(warnings) == 0, warnings


def normalize_server_name(raw_name: str) -> str:
    """
    将注册表的 server ID 转为合法的本地名称
    如 "io.github.user/email-mcp" -> "email-mcp"
    """
    # 取最后一段
    name = raw_name.split("/")[-1]
    # 移除 mcp-server- 前缀
    name = re.sub(r"^mcp-server-", "", name)
    # 只保留字母数字和连字符
    name = re.sub(r"[^a-zA-Z0-9\-_]", "", name)
    return name or "imported-server"
