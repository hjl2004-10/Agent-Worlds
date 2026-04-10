# api/tools_api.py - 工具/技能/MCP/市场路由

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["tools"])


# ========== 工具 ==========

@router.get("/tools/available")
async def api_tools_available():
    from tools import tool as tool_module
    tools = []
    for tool_id, config in tool_module.TOOL_REGISTRY.get("anthropic", {}).items():
        tools.append({
            "id": tool_id,
            "description": config.get("description", ""),
            "enabled": config.get("enabled", True)
        })
    return {"status": "ok", "tools": tools}


@router.get("/tools")
async def api_tools():
    from tools.tool import TOOL_REGISTRY
    task_tools = {}
    for name, config in TOOL_REGISTRY.get("anthropic", {}).items():
        if config.get("enabled", True):
            schema = config.get("input_schema", {})
            task_tools[name] = {
                "description": config.get("description", ""),
                "params": schema.get("properties", {}),
                "required": schema.get("required", [])
            }
    return {"status": "ok", "tools": task_tools}


@router.get("/tool-groups")
async def api_tool_groups():
    from tools import tool as tool_module
    groups = tool_module.get_tool_groups()
    return {"status": "ok", "groups": groups}


@router.post("/tool-groups")
async def api_save_tool_groups(data: dict):
    from tools import tool as tool_module
    groups = data.get("groups", {})
    if not isinstance(groups, dict):
        return {"status": "error", "message": "groups must be a dictionary"}
    for group_name, group_config in groups.items():
        if not group_name.startswith("@"):
            return {"status": "error", "message": f"Group name must start with '@': {group_name}"}
        if not isinstance(group_config, dict):
            return {"status": "error", "message": f"Group config must be a dictionary: {group_name}"}
        if "tools" not in group_config:
            return {"status": "error", "message": f"Group must have 'tools' field: {group_name}"}
    success = tool_module.save_tool_groups(groups)
    if success:
        return {"status": "ok", "groups": groups}
    return {"status": "error", "message": "Failed to save tool groups"}


# ========== 技能 ==========

@router.get("/skills/available")
async def api_skills_available():
    from tools.skill import get_all_skills
    return {"status": "ok", "skills": get_all_skills()}


@router.get("/skills/{name}")
async def api_skill_detail(name: str):
    from tools.skill import get_skill
    data = get_skill(name)
    if not data:
        return {"status": "error", "message": f"技能 '{name}' 不存在"}
    return {"status": "ok", "skill": data}


@router.post("/skills")
async def api_skill_create(data: dict):
    from tools.skill import create_skill
    name = data.get("name")
    if not name:
        return {"status": "error", "message": "缺少 name 字段"}
    return create_skill(
        name=name,
        description=data.get("description", ""),
        tools=data.get("tools", []),
        prompt_text=data.get("prompt_text", ""),
        mcp_server=data.get("mcp_server"),
    )


@router.put("/skills/{name}")
async def api_skill_update(name: str, data: dict):
    from tools.skill import update_skill
    return update_skill(
        name=name,
        description=data.get("description"),
        tools=data.get("tools"),
        prompt_text=data.get("prompt_text"),
        mcp_server=data.get("mcp_server"),
    )


@router.delete("/skills/{name}")
async def api_skill_delete(name: str):
    from tools.skill import delete_skill
    return delete_skill(name)


# ========== MCP ==========

@router.get("/mcp/servers")
async def api_mcp_servers():
    from tools import mcp_manager
    return {"status": "ok", "servers": mcp_manager.list_servers()}


@router.post("/mcp/servers")
async def api_mcp_create_server(data: dict):
    from tools import mcp_manager
    name = data.pop("name", None)
    if not name:
        return {"status": "error", "message": "缺少 name 字段"}
    return mcp_manager.create_or_update_server(name, data)


@router.post("/mcp/servers/{name}/start")
async def api_mcp_start(name: str):
    from tools import mcp_manager
    return mcp_manager.start_server(name)


@router.post("/mcp/servers/{name}/stop")
async def api_mcp_stop(name: str):
    from tools import mcp_manager
    return mcp_manager.stop_server(name)


@router.delete("/mcp/servers/{name}")
async def api_mcp_delete(name: str):
    from tools import mcp_manager
    return mcp_manager.delete_server(name)


# ========== 市场 ==========

@router.get("/marketplace/mcp/search")
async def api_marketplace_mcp_search(q: str = "", limit: int = 20):
    if not q:
        return {"status": "error", "message": "请提供搜索关键词 (q 参数)"}
    from tools import marketplace
    results = marketplace.search_mcp(q, limit)
    return {"status": "ok", "results": results, "count": len(results)}


@router.post("/marketplace/mcp/install")
async def api_marketplace_mcp_install(data: dict):
    from tools import marketplace
    server_info = data.get("server_info")
    if not server_info:
        return {"status": "error", "message": "缺少 server_info"}
    success, message, config = marketplace.install_mcp(
        server_info, data.get("custom_name"), data.get("install_method", "auto"),
    )
    return {"status": "ok" if success else "error", "message": message, "config": config}


@router.get("/marketplace/skills/search")
async def api_marketplace_skills_search(q: str = ""):
    if not q:
        return {"status": "error", "message": "请提供搜索关键词"}
    from tools import marketplace
    results = marketplace.search_skills(q)
    return {"status": "ok", "results": results, "count": len(results)}


@router.post("/marketplace/skills/import")
async def api_marketplace_skills_import(data: dict):
    from tools import marketplace
    url = data.get("url", "")
    if not url:
        return {"status": "error", "message": "缺少 url"}
    success, message = marketplace.import_skill(url, data.get("name"))
    return {"status": "ok" if success else "error", "message": message}
