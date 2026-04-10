# api/world.py - 世界/场景管理路由

from pathlib import Path
from fastapi import APIRouter
from api import _state

router = APIRouter(prefix="/api", tags=["world"])

_PROJECT_ROOT = Path(__file__).parent.parent


@router.get("/world/lore")
async def api_get_lore():
    from tools import io
    from env import map as map_module
    world_file = map_module.get_world_path() / 'world.hjl'
    data = io.read_hjl(str(world_file))
    if data and 'lore' in data:
        return {"status": "ok", "lore": data['lore']}
    return {"status": "ok", "lore": {}}


@router.post("/world/lore")
async def api_update_lore(lore_data: dict):
    from tools import io
    from env import map as map_module
    world_file = map_module.get_world_path() / 'world.hjl'
    data = io.read_hjl(str(world_file)) or {}
    data['lore'] = lore_data
    io.write_hjl(str(world_file), data)
    return {"status": "ok", "lore": lore_data}


@router.get("/world/current")
async def api_get_current_world():
    from env import map as map_module
    from tools import io

    scene_path = map_module.get_scene_path()
    world_path = map_module.get_world_path()

    world_info = None
    world_file = world_path / 'world.hjl'
    if world_file.exists():
        world_data = io.read_hjl(str(world_file))
        if world_data:
            world_info = {
                "world_id": world_data.get("world_id"),
                "display_name": world_data.get("display_name"),
                "genre": world_data.get("genre"),
                "description": world_data.get("description", ""),
                "available_scenes": world_data.get("available_scenes", []),
                "default_scene": world_data.get("default_scene", "default"),
            }

    scene_info = None
    scene_file = scene_path / 'scene.hjl'
    if scene_file.exists():
        scene_data = io.read_hjl(str(scene_file))
        if scene_data:
            scene_info = {
                "scene_id": scene_data.get("scene_id"),
                "display_name": scene_data.get("display_name"),
                "description": scene_data.get("description"),
                "map": scene_data.get("map", {}),
            }

    return {
        "status": "ok",
        "current_world": map_module._current_world,
        "current_scene": map_module._current_scene,
        "world_info": world_info,
        "scene_info": scene_info,
    }


@router.get("/worlds")
async def api_list_worlds():
    import json
    worlds_dir = _PROJECT_ROOT / 'data' / 'worlds'
    worlds = []
    if worlds_dir.exists():
        for world_path in worlds_dir.iterdir():
            if world_path.is_dir():
                world_file = world_path / 'world.hjl'
                if world_file.exists():
                    try:
                        with open(world_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        worlds.append({
                            "world_id": data.get("world_id", world_path.name),
                            "display_name": data.get("display_name", world_path.name),
                            "genre": data.get("genre", "未知"),
                            "description": data.get("description", ""),
                            "available_scenes": data.get("available_scenes", []),
                            "default_scene": data.get("default_scene", "default"),
                        })
                    except Exception:
                        pass
    return {"status": "ok", "worlds": worlds}


@router.post("/world/switch")
async def api_switch_world(data: dict):
    from env import map as map_module
    from tools import io
    import json

    world_id = data.get("world_id")
    if not world_id:
        return {"status": "error", "message": "缺少 world_id"}

    world_path = _PROJECT_ROOT / 'data' / 'worlds' / world_id
    if not world_path.exists():
        return {"status": "error", "message": f"世界不存在: {world_id}"}

    world_file = world_path / 'world.hjl'
    default_scene = "default"
    world_info = None

    if world_file.exists():
        world_data = io.read_hjl(str(world_file))
        if world_data:
            default_scene = world_data.get("default_scene", "default")
            world_info = {
                "world_id": world_data.get("world_id"),
                "display_name": world_data.get("display_name"),
                "genre": world_data.get("genre"),
                "description": world_data.get("description", ""),
                "available_scenes": world_data.get("available_scenes", []),
                "default_scene": default_scene,
            }

    map_module._current_world = world_id
    map_module._current_scene = default_scene

    runtime_file = _PROJECT_ROOT / 'data' / 'runtime' / 'current.hjl'
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    with open(runtime_file, 'w', encoding='utf-8') as f:
        json.dump({"current_world": world_id, "current_scene": default_scene}, f, ensure_ascii=False, indent=2)

    map_module.load_locations()
    map_module.load_obstacles()
    map_module.load_tiles()
    scene_data = _state.load_scene_config()

    from env import time as time_module
    time_module.init()

    _state.reset_world_state()

    return {
        "status": "ok",
        "current_world": world_id,
        "current_scene": default_scene,
        "default_scene": default_scene,
        "world_info": world_info,
        "scene_info": {
            "scene_id": scene_data.get("scene_id"),
            "display_name": scene_data.get("display_name"),
            "description": scene_data.get("description"),
            "map": scene_data.get("map", {}),
        },
    }


@router.post("/scene/switch")
async def api_switch_scene(data: dict):
    from env import map as map_module
    from tools import io
    import json

    scene_id = data.get("scene_id")
    if not scene_id:
        return {"status": "error", "message": "缺少 scene_id"}

    scene_path = map_module.get_world_path() / 'scenes' / scene_id
    if not scene_path.exists():
        return {"status": "error", "message": f"场景不存在: {scene_id}"}

    map_module._current_scene = scene_id

    runtime_file = _PROJECT_ROOT / 'data' / 'runtime' / 'current.hjl'
    with open(runtime_file, 'w', encoding='utf-8') as f:
        json.dump({"current_world": map_module._current_world, "current_scene": scene_id}, f, ensure_ascii=False, indent=2)

    map_module.load_locations()
    map_module.load_obstacles()
    map_module.load_tiles()

    scene_info = None
    scene_file = scene_path / 'scene.hjl'
    if scene_file.exists():
        scene_data = io.read_hjl(str(scene_file))
        if scene_data:
            _state.reset_scene_runtime(scene_data, apply_spawns=True)
            scene_info = {
                "scene_id": scene_data.get("scene_id"),
                "display_name": scene_data.get("display_name"),
                "description": scene_data.get("description"),
                "map": scene_data.get("map", {}),
            }

    return {
        "status": "ok",
        "current_world": map_module._current_world,
        "current_scene": scene_id,
        "scene_info": scene_info,
    }
