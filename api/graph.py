# ============================================
# api/graph.py - 知识图谱查询接口
# 供前端可视化组件拉取节点 + 边, 渲染关系网
# ============================================

from fastapi import APIRouter, Query

from core.graph import graph, engine

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/subgraph")
def get_subgraph(npc: str = Query(default=None), include_events: bool = Query(default=False)):
    """返回当前图谱的节点 + 边, 供前端力导向图渲染。

    npc: 若指定, 只返回该 NPC 的 1~2 跳邻域 (节点+相关边); 否则返回全图
    include_events: 是否包含 :Event 节点与 PARTICIPATED 边 (默认只看关系网)
    """
    if not graph.is_enabled():
        return {"status": "disabled", "nodes": [], "edges": [], "msg": "图谱未启用"}

    if npc:
        # 指定 NPC 的邻域: 该 NPC + 与它有 RELATES 的对端节点 + 之间的边
        nodes_rows = graph.read(
            """
            MATCH (n:Entity {id: toLower($npc)})
            OPTIONAL MATCH (n)-[:RELATES]-(o:Entity)
            WITH collect(DISTINCT n) + collect(DISTINCT o) AS ns
            UNWIND ns AS x
            WITH DISTINCT x WHERE x IS NOT NULL
            RETURN x.name AS id, x.name AS name, x.kind AS kind
            """,
            {"npc": npc},
        )
        edges_rows = graph.read(
            """
            MATCH (a:Entity)-[r:RELATES]->(b:Entity)
            WHERE a.id = toLower($npc) OR b.id = toLower($npc)
            RETURN a.name AS source, b.name AS target, r.type AS label
            """,
            {"npc": npc},
        )
    else:
        nodes_rows = graph.read(
            "MATCH (n:Entity) RETURN n.name AS id, n.name AS name, n.kind AS kind"
        )
        edges_rows = graph.read(
            "MATCH (a:Entity)-[r:RELATES]->(b:Entity) "
            "RETURN a.name AS source, b.name AS target, r.type AS label"
        )

    nodes = [
        {"id": r["id"], "name": r["name"], "kind": r.get("kind") or "person"}
        for r in nodes_rows
        if r.get("id")
    ]

    if include_events:
        ev_nodes = graph.read(
            "MATCH (e:Event) RETURN e.id AS id, e.description AS name, 'event' AS kind"
        )
        nodes.extend(
            {"id": r["id"], "name": (r["name"] or "")[:30], "kind": "event"}
            for r in ev_nodes
        )
        ev_edges = graph.read(
            "MATCH (c:Entity)-[:PARTICIPATED]->(e:Event) "
            "RETURN c.name AS source, e.id AS target, '参与' AS label"
        )
        edges_rows = list(edges_rows) + list(ev_edges)

    edges = [
        {"source": r["source"], "target": r["target"], "label": r.get("label") or ""}
        for r in edges_rows
        if r.get("source") and r.get("target")
    ]

    return {"status": "ok", "nodes": nodes, "edges": edges}


@router.get("/pending")
def list_pending(world_id: str = Query(default=None)):
    """列待归一 entity (pending=true, 陌生新名待确认是不是别名/新实体)。"""
    if not graph.is_enabled():
        return {"status": "disabled", "items": []}
    if world_id:
        rows = graph.read(
            "MATCH (e:Entity {pending: true, world_id: $w}) "
            "RETURN e.id AS id, e.name AS name, e.kind AS kind, e.world_id AS world_id",
            {"w": world_id},
        )
    else:
        rows = graph.read(
            "MATCH (e:Entity {pending: true}) "
            "RETURN e.id AS id, e.name AS name, e.kind AS kind, e.world_id AS world_id"
        )
    return {"status": "ok", "items": rows}


@router.post("/resolve/{entity_id}")
def resolve_pending(entity_id: str, data: dict):
    """确认 pending entity。

    body: {world_id: str, merge_to?: str}
    - merge_to 给定: 归并到该 entity (别名迁移 + 关系改指 + 删 pending)
    - merge_to 不给: 转正式新实体 (pending=false)
    """
    if not graph.is_enabled():
        return {"status": "disabled"}
    world_id = data.get("world_id")
    if not world_id:
        return {"status": "error", "message": "缺少 world_id"}
    merge_to = (data.get("merge_to") or "").strip().lower() or None

    if merge_to:
        ok = engine.merge_pending(entity_id, merge_to, world_id)
        return {"status": "ok" if ok else "failed", "action": "merged", "to": merge_to}
    ok = engine.confirm_pending(entity_id, world_id)
    return {"status": "ok" if ok else "failed", "action": "confirmed"}
