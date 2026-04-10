"""
市场工具 - 业务层 (L1)
搜索注册表、下载 Skill、安装 MCP Server
"""
import json
import os
import shutil
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tools import marketplace_l2


# ========== MCP Server 搜索 ==========

def search_mcp_servers(query: str, limit: int = 20) -> List[dict]:
    """
    从官方注册表搜索 MCP Server

    Args:
        query: 搜索关键词
        limit: 最大结果数

    Returns:
        标准化的 server 信息列表
    """
    from tools.marketplace import REGISTRY_URL, REQUEST_TIMEOUT

    url = f"{REGISTRY_URL}/v0/servers?search={urllib.parse.quote(query)}&limit={limit}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AI_OS/2.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        # API 可能返回 {"servers": [...]} 或直接 [...]
        servers_raw = data if isinstance(data, list) else data.get("servers", data.get("items", []))

        results = []
        for raw in servers_raw[:limit]:
            parsed = marketplace_l2.parse_registry_server(raw)
            if parsed["id"]:
                results.append(parsed)

        return results

    except urllib.error.URLError as e:
        print(f"[Marketplace] 搜索失败: {e}")
        return []
    except Exception as e:
        print(f"[Marketplace] 搜索异常: {e}")
        return []


def get_server_detail(server_id: str) -> Optional[dict]:
    """
    获取单个 server 的详细信息

    Args:
        server_id: server 标识 (如 "io.github.user/email-mcp")

    Returns:
        标准化的 server 信息, 或 None
    """
    from tools.marketplace import REGISTRY_URL, REQUEST_TIMEOUT

    url = f"{REGISTRY_URL}/v0/servers/{urllib.parse.quote(server_id, safe='')}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AI_OS/2.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        return marketplace_l2.parse_registry_server(raw)
    except Exception as e:
        print(f"[Marketplace] 获取详情失败: {e}")
        return None


def install_mcp_server(server_info: dict, custom_name: str = None,
                       install_method: str = "auto") -> Tuple[bool, str, Optional[dict]]:
    """
    安装 MCP Server (生成配置并写入 mcp_servers.json)

    注意: 只写配置，不自动启动。需要用户手动启动。

    Args:
        server_info: 标准化的 server 信息
        custom_name: 自定义名称 (可选)
        install_method: "npm" | "pip" | "remote" | "auto"

    Returns:
        (success, message, config)
    """
    # 生成名称
    name = custom_name or marketplace_l2.normalize_server_name(server_info.get("id", ""))

    # 生成配置
    config = marketplace_l2.generate_mcp_config(server_info, install_method)
    if not config:
        return False, f"无法为 {server_info.get('id', '')} 生成配置 (没有找到可用的安装方式)", None

    # 写入 mcp_manager
    from tools import mcp_manager
    result = mcp_manager.create_or_update_server(name, config)

    if result.get("status") == "ok":
        return True, f"已安装 {name}", config
    else:
        return False, result.get("message", "安装失败"), None


# ========== Skill 导入 ==========

def search_skills_github(query: str) -> List[dict]:
    """
    搜索 GitHub 上的 AI Skills (SKILL.md 格式)

    简单实现: 使用 GitHub API 搜索包含 skill.hjl 或 SKILL.md 的仓库

    Returns:
        [{name, description, url, source}, ...]
    """
    from tools.marketplace import REQUEST_TIMEOUT

    # GitHub code search API
    search_url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query + ' mcp skill')}&per_page=10"

    try:
        req = urllib.request.Request(search_url, headers={
            "User-Agent": "AI_OS/2.0",
            "Accept": "application/vnd.github.v3+json",
        })
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for item in data.get("items", []):
            results.append({
                "name": item.get("name", ""),
                "description": item.get("description", ""),
                "url": item.get("html_url", ""),
                "stars": item.get("stargazers_count", 0),
                "source": "github",
            })
        return results

    except Exception as e:
        print(f"[Marketplace] GitHub 搜索失败: {e}")
        return []


def import_skill_from_url(url: str, skill_name: str = None) -> Tuple[bool, str]:
    """
    从 URL 导入 Skill

    支持格式:
    - GitHub 仓库 URL (下载 skill.hjl + prompt.md)
    - 直接的 JSON URL (skill.hjl 内容)

    Args:
        url: 源 URL
        skill_name: 自定义名称 (可选)

    Returns:
        (success, message)
    """
    from tools.marketplace import REQUEST_TIMEOUT

    try:
        # 尝试判断 URL 类型
        if "github.com" in url:
            return _import_skill_from_github(url, skill_name)
        else:
            return _import_skill_from_direct_url(url, skill_name)
    except Exception as e:
        return False, f"导入失败: {str(e)}"


def _import_skill_from_github(github_url: str, skill_name: str = None) -> Tuple[bool, str]:
    """从 GitHub 仓库导入 skill"""
    from tools.marketplace import SKILLS_DIR, REQUEST_TIMEOUT

    # 解析 GitHub URL -> raw 文件 URL
    # https://github.com/user/repo/tree/main/path -> raw.githubusercontent.com
    parts = github_url.replace("https://github.com/", "").split("/")
    if len(parts) < 2:
        return False, f"无效的 GitHub URL: {github_url}"

    owner, repo = parts[0], parts[1]
    # 尝试找 branch 和 path
    branch = "main"
    sub_path = ""
    if len(parts) > 3 and parts[2] in ("tree", "blob"):
        branch = parts[3]
        sub_path = "/".join(parts[4:]) if len(parts) > 4 else ""

    # 下载 skill.hjl
    base_raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
    skill_hjl_url = f"{base_raw}/{sub_path}/skill.hjl" if sub_path else f"{base_raw}/skill.hjl"

    try:
        req = urllib.request.Request(skill_hjl_url, headers={"User-Agent": "AI_OS/2.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            skill_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, f"未找到 skill.hjl: {skill_hjl_url}"
        return False, f"下载 skill.hjl 失败: {e}"

    # 确定名称
    name = skill_name or skill_data.get("name", "")
    if not name:
        name = repo.replace("mcp-server-", "").replace("skill-", "")

    # 下载 prompt.md
    prompt_file = skill_data.get("prompt_file", "prompt.md")
    prompt_url = f"{base_raw}/{sub_path}/{prompt_file}" if sub_path else f"{base_raw}/{prompt_file}"

    prompt_content = ""
    try:
        req = urllib.request.Request(prompt_url, headers={"User-Agent": "AI_OS/2.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            prompt_content = resp.read().decode("utf-8")
    except Exception:
        prompt_content = f"# {name}\n\n(prompt 文件下载失败，请手动编辑)"

    # 安全扫描 prompt
    is_safe, warnings = marketplace_l2.scan_prompt_safety(prompt_content)
    if not is_safe:
        warning_text = "\n".join(f"  ⚠️ {w}" for w in warnings)
        return False, f"安全扫描未通过:\n{warning_text}\n\n如需强制导入，请手动创建 skill"

    # 写入本地
    skill_dir = SKILLS_DIR / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # 添加来源信息
    skill_data["source"] = github_url
    skill_data["name"] = name

    with open(skill_dir / "skill.hjl", "w", encoding="utf-8") as f:
        json.dump(skill_data, f, ensure_ascii=False, indent=2)

    with open(skill_dir / prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt_content)

    # 如果 skill 依赖 MCP Server，提示用户安装
    mcp_info = skill_data.get("mcp_server")
    msg = f"✅ Skill '{name}' 已导入到 data/skills/{name}/"
    if mcp_info:
        msg += f"\n⚠️ 此 skill 依赖 MCP Server，请在 MCP 页签安装: {mcp_info}"

    return True, msg


def _import_skill_from_direct_url(url: str, skill_name: str = None) -> Tuple[bool, str]:
    """从直接 URL 导入 (JSON 格式的 skill.hjl)"""
    from tools.marketplace import SKILLS_DIR, REQUEST_TIMEOUT

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AI_OS/2.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            content = resp.read().decode("utf-8")

        skill_data = json.loads(content)
        name = skill_name or skill_data.get("name", "imported-skill")

        skill_dir = SKILLS_DIR / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        with open(skill_dir / "skill.hjl", "w", encoding="utf-8") as f:
            json.dump(skill_data, f, ensure_ascii=False, indent=2)

        # 创建空 prompt
        prompt_file = skill_data.get("prompt_file", "prompt.md")
        with open(skill_dir / prompt_file, "w", encoding="utf-8") as f:
            f.write(f"# {name}\n\n(请编辑此文件添加技能引导词)")

        return True, f"✅ Skill '{name}' 已导入 (请编辑 prompt.md)"

    except json.JSONDecodeError:
        return False, "URL 内容不是有效的 JSON"
    except Exception as e:
        return False, f"导入失败: {str(e)}"


def delete_imported_skill(name: str) -> Tuple[bool, str]:
    """删除已导入的 skill"""
    from tools.marketplace import SKILLS_DIR

    skill_dir = SKILLS_DIR / name
    if not skill_dir.exists():
        return False, f"Skill '{name}' 不存在"

    shutil.rmtree(skill_dir)
    return True, f"已删除 Skill '{name}'"


def list_local_skills() -> List[dict]:
    """列出所有本地 skill"""
    from tools.marketplace import SKILLS_DIR

    skills = []
    if not SKILLS_DIR.exists():
        return skills

    for d in sorted(SKILLS_DIR.iterdir()):
        if d.is_dir() and (d / "skill.hjl").exists():
            try:
                with open(d / "skill.hjl", "r", encoding="utf-8") as f:
                    data = json.load(f)
                skills.append({
                    "name": data.get("name", d.name),
                    "description": data.get("description", ""),
                    "tools": data.get("tools", []),
                    "mcp_server": data.get("mcp_server"),
                    "source": data.get("source", "local"),
                })
            except Exception:
                skills.append({"name": d.name, "description": "(读取失败)", "source": "local"})

    return skills
