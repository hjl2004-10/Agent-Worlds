# ============================================
# api/__init__.py - 路由注册器
# 职责: 将所有子路由模块注册到 FastAPI app
# ============================================

from fastapi import FastAPI


def register_all_routers(app: FastAPI):
    """注册所有 API 路由模块到 app"""
    from api.status import router as status_router
    from api.god import router as god_router
    from api.npc import router as npc_router
    from api.conversation import router as conversation_router
    from api.tools_api import router as tools_router
    from api.world import router as world_router
    from api.tasks import router as tasks_router
    from api.mailbox import router as mailbox_router
    from api.misc import router as misc_router
    from api.wechat import router as wechat_router

    app.include_router(status_router)
    app.include_router(god_router)
    app.include_router(npc_router)
    app.include_router(conversation_router)
    app.include_router(tools_router)
    app.include_router(world_router)
    app.include_router(tasks_router)
    app.include_router(mailbox_router)
    app.include_router(misc_router)
    app.include_router(wechat_router)
