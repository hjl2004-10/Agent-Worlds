"""
市场工具 - 总控层 (L0)
配置 + 接口定义
"""
from pathlib import Path

# ========== 配置 ==========

# 官方 MCP 注册表 API
REGISTRY_URL = "https://registry.modelcontextprotocol.io"

# HTTP 请求超时 (秒)
REQUEST_TIMEOUT = 15

# Skill 存储目录 (初始化时设置)
SKILLS_DIR = None


def init(project_root: str):
    """初始化市场模块"""
    global SKILLS_DIR
    SKILLS_DIR = Path(project_root) / "data" / "skills"
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)


# ========== 接口 (转发到 L1) ==========

def search_mcp(query: str, limit: int = 20):
    """搜索 MCP Server"""
    from tools.marketplace_l1 import search_mcp_servers
    return search_mcp_servers(query, limit)


def install_mcp(server_info: dict, custom_name: str = None, method: str = "auto"):
    """安装 MCP Server"""
    from tools.marketplace_l1 import install_mcp_server
    return install_mcp_server(server_info, custom_name, method)


def search_skills(query: str):
    """搜索 Skill (GitHub)"""
    from tools.marketplace_l1 import search_skills_github
    return search_skills_github(query)


def import_skill(url: str, name: str = None):
    """从 URL 导入 Skill"""
    from tools.marketplace_l1 import import_skill_from_url
    return import_skill_from_url(url, name)


def list_skills():
    """列出本地 Skill"""
    from tools.marketplace_l1 import list_local_skills
    return list_local_skills()
