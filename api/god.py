# api/god.py - 上帝模式路由

from fastapi import APIRouter
from core import state_bus
from core.lock import npcs_lock
from env.map import MAP_WIDTH, MAP_HEIGHT
from api import _state

router = APIRouter(prefix="/api/god", tags=["god"])


def _clamp_pos(x, y):
    """钳制坐标到地图边界 (与前端预测的钳制一致: 2 ~ MAP-2)"""
    x = max(2.0, min(float(MAP_WIDTH) - 2.0, float(x)))
    y = max(2.0, min(float(MAP_HEIGHT) - 2.0, float(y)))
    return x, y


def _sync_client_pos(npc, body):
    """采信前端预测位置 (松键/转向时同步，消除校正回跳)"""
    if not isinstance(body, dict):
        return
    try:
        if 'x' in body and 'y' in body:
            npc.x, npc.y = _clamp_pos(body['x'], body['y'])
    except (TypeError, ValueError):
        pass


@router.post("/select/{npc_name}")
async def god_select(npc_name: str):
    return state_bus.submit("god_select", {"npc_name": npc_name}, wait=True)


@router.post("/deselect")
async def god_deselect(request: dict = {}):
    return state_bus.submit("god_deselect", request, wait=True)


@router.post("/move/{direction}")
async def god_move(direction: str, request: dict = {}):
    """上帝模式移动 — 采信前端当前位置 + 设置方向，移动由驱动循环按统一速度推进"""
    if direction not in ['up', 'down', 'left', 'right']:
        return {"status": "error", "message": "Invalid direction"}

    with npcs_lock:
        for npc in _state.get_npcs():
            if npc.god_controlled:
                _sync_client_pos(npc, request)
                npc.god_move_direction = direction
                return {"status": "ok", "npc": npc.name,
                        "direction": direction, "x": npc.x, "y": npc.y}

    return {"status": "error", "message": "No NPC selected"}


@router.post("/stop")
async def god_stop(request: dict = {}):
    """停止移动 — 采信前端最终位置并清除方向 (原子完成，避免轮询校正回跳)"""
    with npcs_lock:
        for npc in _state.get_npcs():
            if npc.god_controlled:
                _sync_client_pos(npc, request)
                npc.god_move_direction = None
                return {"status": "ok", "npc": npc.name, "x": npc.x, "y": npc.y}

    return {"status": "ok"}


@router.get("/status")
async def god_status():
    selected = None
    for npc in _state.get_npcs():
        if npc.god_controlled:
            selected = npc.name
            break
    return {"god_mode": selected is not None, "selected_npc": selected}
