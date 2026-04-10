# api/npc.py - NPC 管理路由 (配置/工具/导入导出/背包)

from fastapi import APIRouter
from core import state_bus
from api import _state

router = APIRouter(prefix="/api", tags=["npc"])


@router.get("/npc/{npc_name}/tools")
async def api_npc_tools(npc_name: str):
    for npc in _state.get_npcs():
        if npc.name.lower() == npc_name.lower():
            return {"status": "ok", "npc": npc.name, "tools": npc.memory.get('rom_tools', [])}
    return {"status": "error", "message": "NPC not found"}


@router.post("/npc/{npc_name}/tools")
async def api_npc_set_tools(npc_name: str, data: dict):
    tools = data.get("tools", [])
    if not isinstance(tools, list):
        return {"status": "error", "message": "tools must be a list"}
    return state_bus.submit("npc_tools_set", {"npc_name": npc_name, "tools": tools}, wait=True)


@router.get("/npc/{npc_name}/config")
async def api_npc_config(npc_name: str):
    for npc in _state.get_npcs():
        if npc.name.lower() == npc_name.lower():
            return {"status": "ok", "config": _state.build_npc_config(npc)}
    return {"status": "error", "message": f"NPC '{npc_name}' not found"}


@router.post("/npc/{npc_name}/config")
async def api_npc_update_config(npc_name: str, data: dict):
    return state_bus.submit("npc_config_update", {"npc_name": npc_name, "data": data}, wait=True)


@router.patch("/npc/{npc_name}/enabled")
async def api_npc_enabled(npc_name: str, data: dict):
    enabled = data.get("enabled", True)
    return state_bus.submit("npc_enabled", {"npc_name": npc_name, "enabled": enabled}, wait=True)


@router.post("/npc/export")
async def api_npc_export(data: dict):
    names = data.get("names", [])
    if not names:
        return {"status": "error", "message": "No NPCs selected for export"}
    return state_bus.submit("npc_export", {"names": names}, wait=True)


@router.post("/npc/import")
async def api_npc_import(data: dict):
    npcs_data = data.get("npcs", [])
    overwrite = data.get("overwrite", False)
    if not npcs_data:
        return {"status": "error", "message": "No NPC data provided"}
    return state_bus.submit("npc_import", {"npcs": npcs_data, "overwrite": overwrite}, wait=True)


@router.post("/npc/create")
async def api_npc_create(data: dict):
    name = data.get("name", "").strip()
    if not name:
        return {"status": "error", "message": "NPC name is required"}
    return state_bus.submit("npc_create", {"data": data}, wait=True)


@router.get("/inventory/{npc_name}")
async def api_inventory(npc_name: str):
    for npc in _state.get_npcs():
        if npc.name.lower() == npc_name.lower():
            return {
                "status": "ok",
                "npc": npc.name,
                "schema": npc.memory.get('inventory_schema', {}),
                "inventory": npc.memory.get('inventory', {})
            }
    return {"status": "error", "message": f"NPC '{npc_name}' not found"}


@router.post("/inventory/{npc_name}")
async def api_update_inventory(npc_name: str, data: dict):
    return state_bus.submit("inventory_update", {"npc_name": npc_name, "data": data}, wait=True)


@router.get("/npc/market")
async def api_npc_market():
    """NPC 市场展示数据 (轻量摘要，不含完整历史)"""
    npcs = []
    for npc in _state.get_npcs():
        npcs.append({
            "name": npc.name,
            "sprite_id": npc.sprite_id,
            "description": npc.memory.get('rom_personality', '')[:120],
            "skills": npc.memory.get('rom_skills', []),
            "tools": npc.memory.get('rom_tools', []),
            "groups": npc.memory.get('rom_groups', []),
            "initiative": npc.initiative,
            "max_initiative": npc.max_initiative,
            "history_count": len(npc.memory.get('hdd_history', [])),
            "is_player": npc.is_player,
            "enabled": npc.enabled,
            "has_mcp": len(npc.memory.get('mcp_servers', [])) > 0,
            "wechat_status": npc.wechat_binding.get("status", "unbound") if hasattr(npc, 'wechat_binding') else "unbound",
            "llm_channel": npc.llm_channel,
            "inventory_count": len(npc.memory.get('inventory', {})),
        })
    return {"status": "ok", "npcs": npcs}
