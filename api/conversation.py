# api/conversation.py - 对话系统路由

from fastapi import APIRouter
from api import _state

router = APIRouter(prefix="/api", tags=["conversation"])


@router.post("/player/input")
async def player_input(data: dict):
    player_name = data.get("player_name", "Player")
    text = data.get("text", "")
    if not text:
        return {"status": "error", "message": "Empty text"}

    from core.social.social_l1 import set_player_input
    set_player_input(player_name, text)
    return {"status": "ok", "player": player_name}


@router.get("/conversation/state")
async def conversation_state():
    from core.social.social_l1 import get_conversation_state, get_all_conversation_states
    from core.social.conversation_task import get_active_count, MAX_CONCURRENT_CONVERSATIONS

    return {
        **get_conversation_state(),
        "conversations": get_all_conversation_states(),
        "active_count": get_active_count(),
        "max_concurrent": MAX_CONCURRENT_CONVERSATIONS,
    }


@router.post("/conversation/end")
async def end_conversation():
    from core.social.social_l1 import end_conversation
    end_conversation()
    return {"status": "ok"}


@router.post("/conversation/stop_all")
async def stop_all_conversations():
    """强制停止所有活跃对话 (包括NPC-NPC、微信、定时器等)"""
    from core.social.conversation_task import force_stop_all
    count = force_stop_all()
    return {"status": "ok", "stopped": count}


@router.get("/conversation/ram/{npc_name}")
async def get_conversation_ram(npc_name: str):
    from core.social.social_l1 import get_conversation_partners
    partners = get_conversation_partners()

    for npc in _state.get_npcs():
        if npc.name.lower() == npc_name.lower():
            ram_buffer = npc.memory.get('ram_buffer', [])
            return {
                "status": "ok",
                "npc_name": npc.name,
                "partner": partners.get(npc.name),
                "items": ram_buffer,
                "total": len(ram_buffer)
            }
    return {"status": "error", "message": f"NPC '{npc_name}' not found"}


@router.get("/memory/{npc_name}")
async def get_memory(npc_name: str, offset: int = 0, limit: int = 10):
    import json
    from pathlib import Path

    hjl_path = Path(__file__).parent.parent / "data" / "individuals" / f"{npc_name.lower()}.hjl"
    if not hjl_path.exists():
        return {"status": "error", "message": f"NPC '{npc_name}' not found"}

    try:
        with open(hjl_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        history = data.get("memory", {}).get("history", [])
        total = len(history)
        start = max(0, total - offset - limit)
        end = total - offset
        items = history[start:end]

        return {
            "status": "ok",
            "npc_name": npc_name,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": start > 0,
            "items": items
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
