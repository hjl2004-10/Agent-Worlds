# api/wechat.py - 微信绑定路由

from fastapi import APIRouter
from api import _state

router = APIRouter(prefix="/api/wechat", tags=["wechat"])


@router.post("/bind")
async def bind_npc(data: dict):
    """发起绑定 (获取二维码)"""
    npc_name = data.get("npc_name", "")
    if not npc_name:
        return {"status": "error", "message": "缺少 npc_name"}

    from core.wechat import wechat
    result = wechat.bind_npc(npc_name)
    return result


@router.post("/unbind")
async def unbind_npc(data: dict):
    """解除绑定"""
    npc_name = data.get("npc_name", "")
    if not npc_name:
        return {"status": "error", "message": "缺少 npc_name"}

    from core.wechat import wechat
    result = wechat.unbind_npc(npc_name)
    return result


@router.get("/status/{npc_name}")
async def get_status(npc_name: str):
    """查询绑定状态"""
    from core.wechat import wechat
    return wechat.get_bind_status(npc_name)


@router.get("/bindings")
async def get_all_bindings():
    """获取所有绑定"""
    from core.wechat import wechat_l1
    return {
        "status": "ok",
        "bindings": wechat_l1.get_all_bindings(),
    }


@router.post("/send")
async def send_message(data: dict):
    """手动发送微信消息 (调试用)"""
    npc_name = data.get("npc_name", "")
    text = data.get("text", "")
    if not npc_name or not text:
        return {"status": "error", "message": "缺少 npc_name 或 text"}

    from core.wechat import wechat_l1
    wechat_l1.send_npc_reply(npc_name, text)
    return {"status": "ok"}
