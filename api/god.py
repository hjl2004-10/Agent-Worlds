# api/god.py - 上帝模式路由

from fastapi import APIRouter
from core import state_bus
from core.lock import npcs_lock
from core.drive import drive_l2 as l2
from env.map import MAP_WIDTH, MAP_HEIGHT
from core.drive.drive import STEP_SIZE
from api import _state

router = APIRouter(prefix="/api/god", tags=["god"])

# 上帝模式步长 (与 drive_l1 一致)
GOD_STEP = STEP_SIZE * 10


@router.post("/select/{npc_name}")
async def god_select(npc_name: str):
    return state_bus.submit("god_select", {"npc_name": npc_name}, wait=True)


@router.post("/deselect")
async def god_deselect(request: dict = {}):
    return state_bus.submit("god_deselect", request, wait=True)


@router.post("/move/{direction}")
async def god_move(direction: str):
    """上帝模式移动 — 绕过 state_bus，直接在 API 层同步修改坐标"""
    if direction not in ['up', 'down', 'left', 'right']:
        return {"status": "error", "message": "Invalid direction"}

    with npcs_lock:
        for npc in _state.get_npcs():
            if npc.god_controlled:
                npc.god_move_direction = direction
                npc.x, npc.y = l2.god_mode_step(
                    npc.x, npc.y, direction, GOD_STEP, MAP_WIDTH, MAP_HEIGHT
                )
                return {"status": "ok", "npc": npc.name,
                        "direction": direction, "x": npc.x, "y": npc.y}

    return {"status": "error", "message": "No NPC selected"}


@router.post("/stop")
async def god_stop():
    return state_bus.submit("god_stop", wait=True)


@router.get("/status")
async def god_status():
    selected = None
    for npc in _state.get_npcs():
        if npc.god_controlled:
            selected = npc.name
            break
    return {"god_mode": selected is not None, "selected_npc": selected}
