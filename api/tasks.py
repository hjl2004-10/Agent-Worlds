# api/tasks.py - 任务与定时器路由

from fastapi import APIRouter
from core import state_bus
from api import _state

router = APIRouter(prefix="/api", tags=["tasks"])


# ========== 任务 ==========

@router.post("/tasks/assign")
async def tasks_assign(data: dict):
    target = data.get("target", "")
    hint = data.get("hint", "")
    tool_hint = data.get("tool_hint")

    if not target or not hint:
        return {"status": "error", "message": "Missing target or hint"}

    npc_names = [npc.name for npc in _state.get_npcs()]
    if target not in npc_names:
        return {"status": "error", "message": f"NPC '{target}' not found"}

    return state_bus.submit(
        "task_assign",
        {"target": target, "hint": hint, "tool_hint": tool_hint, "source": "Player"},
        wait=True
    )


@router.get("/tasks/all")
async def tasks_get_all():
    """获取所有 NPC 的任务"""
    from tools import task as task_module
    pool = task_module.get_all_tasks()
    return {"status": "ok", "pool": pool}


@router.get("/tasks/{npc_name}")
async def tasks_get(npc_name: str):
    from tools import task as task_module
    tasks = task_module.get_tasks_for(npc_name)
    return {"status": "ok", "npc": npc_name, "tasks": tasks}


@router.delete("/tasks/{npc_name}")
async def tasks_delete(npc_name: str, data: dict):
    hint = data.get("hint", "")
    if not hint:
        return {"status": "error", "message": "Missing hint"}
    return state_bus.submit("task_delete", {"npc_name": npc_name, "hint": hint}, wait=True)


@router.patch("/tasks/{npc_name}/complete")
async def tasks_complete(npc_name: str, data: dict):
    hint = data.get("hint", "")
    if not hint:
        return {"status": "error", "message": "Missing hint"}
    return state_bus.submit("task_complete", {"npc_name": npc_name, "hint": hint}, wait=True)


# ========== 定时器 ==========

@router.get("/timers")
async def api_timers():
    from tools import timer as timer_module
    timers = timer_module.get_all_timers()
    return {"status": "ok", "timers": timers}


@router.get("/timers/{npc_name}")
async def api_npc_timers(npc_name: str):
    from tools import timer as timer_module
    timers = timer_module.get_timers_for(npc_name)
    return {"status": "ok", "npc": npc_name, "timers": timers}


@router.post("/timers/create")
async def api_create_timer(data: dict):
    name = data.get("name", "")
    description = data.get("description", "")
    target = data.get("target", "")
    interval_ticks = data.get("interval_ticks", 120)
    max_triggers = data.get("max_triggers", -1)

    if not name or not description or not target:
        return {"status": "error", "message": "Missing name, description or target"}

    npc_names = [npc.name for npc in _state.get_npcs()]
    if target not in npc_names:
        return {"status": "error", "message": f"NPC '{target}' not found"}

    return state_bus.submit("timer_create", {
        "name": name, "description": description, "target": target,
        "interval_ticks": interval_ticks, "max_triggers": max_triggers,
    }, wait=True)


@router.delete("/timers/{timer_id}")
async def api_delete_timer(timer_id: str):
    return state_bus.submit("timer_delete", {"timer_id": timer_id}, wait=True)


@router.patch("/timers/{timer_id}")
async def api_update_timer(timer_id: str, data: dict):
    return state_bus.submit("timer_update", {"timer_id": timer_id, "data": data}, wait=True)
