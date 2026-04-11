# api/status.py - 状态与地图查询路由

from fastapi import APIRouter
from core.lock import npcs_lock
from env import time as world_time
from api import _state

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status")
async def api_status():
    info = world_time.get_time_info()
    npcs = _state.get_npcs()
    return {
        "tick": _state.get_tick(),
        "npc_count": len(npcs),
        "date": f"{info['year']}年{info['month']}月{info['day']}日",
        "date_iso": f"{info['year']}-{info['month']:02d}-{info['day']:02d}",
        "time": info['time_str'],
        "period": info['period'],
        "period_key": info.get('period_key', ''),
    }


@router.get("/npcs")
async def api_npcs():
    with npcs_lock:
        return [{
            "name": npc.name,
            "x": npc.x,
            "y": npc.y,
            "initiative": npc.initiative,
            "is_talking": npc.is_talking,
            "is_player": npc.is_player,
            "ban_target": npc.ban_target_uuid,
            "god_controlled": npc.god_controlled,
            "god_move_direction": npc.god_move_direction,
            "walk_mode": npc.walk_mode,
            "sprite_id": npc.sprite_id,
            "tools": npc.memory.get('rom_tools', []),
            "enabled": npc.enabled
        } for npc in _state.get_npcs()]


@router.get("/locations")
async def api_locations():
    from env import map as map_module
    return {
        "status": "ok",
        "map_width": map_module.MAP_WIDTH,
        "map_height": map_module.MAP_HEIGHT,
        "locations": [
            {"name": name, "x": info["x"], "y": info["y"], "building": info.get("building"), "desc": info.get("desc", "")}
            for name, info in map_module.LOCATIONS.items()
        ]
    }


@router.get("/obstacles")
async def api_obstacles():
    from env import map as map_module
    return {"status": "ok", "obstacles": map_module.get_obstacles()}


@router.get("/tiles")
async def api_tiles():
    from env import map as map_module
    return {
        "status": "ok",
        "tileSize": 16,
        "mapWidth": map_module.MAP_WIDTH,
        "mapHeight": map_module.MAP_HEIGHT,
        "tiles": map_module.get_tiles()
    }


@router.get("/event")
async def api_event():
    return {"event": _state.get_last_event()}


@router.get("/events")
async def api_events(limit: int = 50):
    """获取事件历史 (最新在前)"""
    history = _state.get_event_history()
    events = list(reversed(history[-limit:]))
    return {"status": "ok", "events": events}


@router.get("/players")
async def api_players():
    return [{
        "name": npc.name,
        "x": npc.x,
        "y": npc.y,
        "is_talking": npc.is_talking
    } for npc in _state.get_npcs() if npc.is_player]
