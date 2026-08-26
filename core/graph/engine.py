# ============================================
# core/graph/engine.py - 知识图谱写入处理层
# 职责: 实体归一 (别名表 + 待归一队列)
#        把名字收敛到规范 entity_id, 避免碎片化(Boss/老板/他 各建节点)。
# ============================================

from core.graph import graph
from core.graph import graph_l2 as l2


def resolve_entity(name, world_id, kind='person'):
    """把名字归一到规范 entity_id。

    1. 精确命中 id (name.lower()) 或命中某 entity 的 aliases → 归一返回
    2. 未命中 → 建 pending entity (陌生新名, 进待归一队列), 返回其 id

    已知 NPC 名应由 graph.ensure_entities 启动时预建为正式 entity,
    这样命中精确 id 不进 pending; 只有真正陌生的名字才 pending。

    返回: 规范 entity_id (小写)。未启用时降级为直接 name.lower()。
    """
    if not graph.is_enabled():
        return (name or '').strip().lower()

    norm = (name or '').strip().lower()
    if not norm:
        return norm

    # 1. 查规范 id / 别名
    rows = graph.read(l2.CYPHER_RESOLVE_ENTITY, {'name': norm, 'world_id': world_id})
    if rows:
        return rows[0]['id']

    # 2. 未命中, 建 pending entity (待归一队列)
    from env import time as world_time
    now = world_time.get_datetime_str()
    graph.write(l2.CYPHER_CREATE_PENDING_ENTITY, {
        'eid': norm, 'name': name.strip(), 'kind': kind,
        'world_id': world_id, 'now': now,
    })
    return norm


def confirm_pending(entity_id, world_id):
    """确认 pending entity 为正式 (pending=false)。返回是否成功。"""
    if not graph.is_enabled():
        return False
    return graph.write(
        "MATCH (e:Entity {id: $eid, world_id: $wid}) SET e.pending = false",
        {'eid': entity_id.lower(), 'wid': world_id},
    )


def merge_pending(entity_id, target_id, world_id):
    """把 pending entity 归并到已有 target: 关系改指 + 别名迁移 + 删 pending。

    用于确认'小王其实就是 Boss' —— 把 pending 节点'小王'的所有关系改指到 boss,
    把'小王'加进 boss 的 aliases, 然后删掉'小王'节点。

    用 graph.read/write (自动提交, 每步独立事务) 而非 write_tx ——
    managed transaction 里多段 tx.run 的未 consume Result 会让 DETACH DELETE 失效。
    牺牲一点原子性换可靠性。
    """
    if not graph.is_enabled():
        return False
    from env import time as world_time
    now = world_time.get_datetime_str()
    tick = world_time.get_tick()
    eid = entity_id.lower()
    target = target_id.lower()

    # 1. pending 的出边改指 target (复制 type/observer/confidence/intimacy/note)
    out_rels = graph.read(
        "MATCH (p:Entity {id: $eid, world_id: $wid})-[r:RELATES]->(o:Entity) "
        "WHERE o.id <> $target "
        "RETURN r.type AS type, r.observer AS obs, r.confidence AS conf, "
        "r.intimacy AS inti, r.note AS note, o.id AS oid, o.name AS oname, o.kind AS okind",
        {'eid': eid, 'wid': world_id, 'target': target},
    )
    for rel in out_rels:
        graph.write(l2.CYPHER_WRITE_RELATION, {
            'subject_id': target, 'subject_name': target, 'subject_kind': 'person',
            'object_id': rel['oid'], 'object_name': rel['oname'], 'object_kind': rel['okind'],
            'relation': rel['type'], 'observer': rel['obs'],
            'confidence': rel['conf'] or 'medium',
            'world_id': world_id, 'intimacy': rel['inti'], 'note': rel['note'] or '',
            'now': now, 'tick': tick,
        })

    # 2. pending 的入边改指 target
    in_rels = graph.read(
        "MATCH (x:Entity)-[r:RELATES]->(p:Entity {id: $eid, world_id: $wid}) "
        "WHERE x.id <> $target "
        "RETURN r.type AS type, r.observer AS obs, r.confidence AS conf, "
        "r.intimacy AS inti, r.note AS note, x.id AS xid, x.name AS xname, x.kind AS xkind",
        {'eid': eid, 'wid': world_id, 'target': target},
    )
    for rel in in_rels:
        graph.write(l2.CYPHER_WRITE_RELATION, {
            'subject_id': rel['xid'], 'subject_name': rel['xname'], 'subject_kind': rel['xkind'],
            'object_id': target, 'object_name': target, 'object_kind': 'person',
            'relation': rel['type'], 'observer': rel['obs'],
            'confidence': rel['conf'] or 'medium',
            'world_id': world_id, 'intimacy': rel['inti'], 'note': rel['note'] or '',
            'now': now, 'tick': tick,
        })

    # 3. 别名迁移 + 删 pending (DETACH DELETE 清剩余边)
    graph.write(
        "MATCH (p:Entity {id: $eid, world_id: $wid}), (t:Entity {id: $target, world_id: $wid}) "
        "SET t.aliases = coalesce(t.aliases, []) + "
        "  CASE WHEN coalesce(p.name,'') <> '' AND NOT p.name IN coalesce(t.aliases,[]) "
        "       THEN [p.name] ELSE [] END "
        "DETACH DELETE p",
        {'eid': eid, 'wid': world_id, 'target': target},
    )
    return True
