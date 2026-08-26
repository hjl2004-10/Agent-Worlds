# ============================================
# api/config.py - 运行时配置接口 (memory + graph)
# 供前端配置面板读写记忆/图谱的 limit 等参数, 改完即时生效
# ============================================

from fastapi import APIRouter

from core.prompt import prompt
from core.graph import graph

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def get_config():
    """读 memory + graph 运行时配置。"""
    return {
        "status": "ok",
        "memory": dict(prompt.CONFIG),
        "graph": graph.get_config(),
    }


@router.post("")
def set_config(data: dict):
    """更新 memory/graph 配置并持久化 (前端改完即时生效)。

    body: {memory?: {...}, graph?: {...}} 只传要改的字段。
    """
    memory = data.get("memory") or {}
    graph_cfg = data.get("graph") or {}
    ok_m = prompt.set_prompt_config(memory) if memory else True
    ok_g = graph.set_config(graph_cfg) if graph_cfg else True
    return {
        "status": "ok" if (ok_m and ok_g) else "failed",
        "memory": dict(prompt.CONFIG),
        "graph": graph.get_config(),
    }
