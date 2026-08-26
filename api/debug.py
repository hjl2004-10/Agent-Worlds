# ============================================
# api/debug.py - 调试接口 (LLM 调用日志)
# 供前端调试面板按 NPC 查看每次对话的请求/返回/工具调用
# ============================================

from fastapi import APIRouter, Query

from core.debug import debug_log

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/llm_logs")
def list_llm_logs(npc: str = Query(default=None), limit: int = Query(default=50)):
    """LLM 调用日志列表 (摘要, 最新在前)。

    npc: 过滤 speaker 或 listener 等于该 NPC 的记录
    limit: 返回条数
    """
    return {"status": "ok", "items": debug_log.get_logs(npc=npc, limit=limit)}


@router.get("/llm_logs/{log_id}")
def get_llm_log(log_id: int):
    """单条 LLM 调用详情 (含完整 messages/response/tool_calls)。"""
    entry = debug_log.get_log(log_id)
    if entry is None:
        return {"status": "not_found"}
    return {"status": "ok", "entry": entry}
