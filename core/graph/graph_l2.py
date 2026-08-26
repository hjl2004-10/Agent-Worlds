# ============================================
# core/graph/graph_l2.py - 知识图谱原子层
# 职责: Cypher 模板常量 + 查询结果到文本的纯格式化函数 (无状态、无 IO)
#
# 设计: 通用知识图谱 —— 节点统一 :Entity {id, name, kind, world_id},
#       kind 区分 person/item/place/topic/concept 等;
#       关系统一 :RELATES {type}, type 自由填, 可连任意两个实体。
#       人不再是特殊节点, 物/地点/概念都能进图。
# ============================================

# ============================================
# 写侧 Cypher
# ============================================

# 写一条通用关系: (主体:Entity)-[:RELATES {type}]->(客体:Entity)
# 主体/客体按需懒建, kind 标识类型; 同一对实体可有多个不同 type 的关系
CYPHER_WRITE_RELATION = """
MERGE (s:Entity {id: $subject_id, world_id: $world_id})
  ON CREATE SET s.name = $subject_name, s.kind = $subject_kind, s.created_at = $now
MERGE (o:Entity {id: $object_id, world_id: $world_id})
  ON CREATE SET o.name = $object_name, o.kind = $object_kind, o.created_at = $now
WITH s, o
MERGE (s)-[r:RELATES {type: $relation, observer: $observer}]->(o)
  ON CREATE SET r.created_tick = $tick
SET r.updated_at = $now,
    r.updated_tick = $tick,
    r.confidence = $confidence,
    r.ts = $now
FOREACH(_ IN CASE WHEN $intimacy IS NOT NULL THEN [1] ELSE [] END |
  SET r.intimacy = $intimacy)
FOREACH(_ IN CASE WHEN ($note IS NOT NULL) AND ($note <> '') THEN [1] ELSE [] END |
  SET r.note = $note)
RETURN r.type AS type
"""

# 写事件: MERGE Event + 参与者(均 :Entity kind=person) PARTICIPATED 边
CYPHER_WRITE_EVENT = """
MERGE (e:Event {id: $event_id})
  ON CREATE SET e.description = $description, e.world_id = $world_id,
                 e.tick = $tick, e.datetime = $now, e.created_by = $recorder_id,
                 e.confidence = $confidence
WITH e
UNWIND $participants AS p
MERGE (c:Entity {id: p.id, world_id: $world_id})
  ON CREATE SET c.name = p.name, c.kind = 'person', c.created_at = $now
MERGE (c)-[:PARTICIPATED]->(e)
RETURN e.id AS id
"""

# 事件时序链 (同一记录者的相邻事件)
CYPHER_LINK_NEXT = """
MATCH (prev:Event {created_by: $recorder_id, world_id: $world_id})
WHERE prev.id <> $event_id AND prev.tick <= $tick
WITH prev ORDER BY prev.tick DESC LIMIT 1
MATCH (cur:Event {id: $event_id})
MERGE (prev)-[:NEXT]->(cur)
"""

# 事件因果链 (可选)
CYPHER_LINK_CAUSED = """
MATCH (cause:Event {id: $cause_id}), (cur:Event {id: $event_id})
MERGE (cause)-[:CAUSED]->(cur)
"""

# ============================================
# 实体归一 (别名表 + 待归一队列)
# ============================================

# 查规范 id: 精确命中 id, 或命中某 entity 的 aliases
CYPHER_RESOLVE_ENTITY = """
MATCH (e:Entity {world_id: $world_id})
WHERE e.id = $name OR $name IN coalesce(e.aliases, [])
RETURN e.id AS id
LIMIT 1
"""

# 建待归一 entity (陌生新名, pending=true, 进待归一队列)
CYPHER_CREATE_PENDING_ENTITY = """
MERGE (e:Entity {id: $eid, world_id: $world_id})
  ON CREATE SET e.name = $name, e.kind = $kind, e.aliases = [],
                 e.pending = true, e.created_at = $now
RETURN e.id AS id
"""

# 启动预建正式 entity (已知 NPC; 已存在的 pending 会被转正式)
CYPHER_ENSURE_ENTITY = """
MERGE (e:Entity {id: $eid, world_id: $world_id})
  ON CREATE SET e.name = $name, e.kind = $kind, e.aliases = [],
                 e.pending = false, e.created_at = $now
  ON MATCH SET e.pending = false
RETURN e.id AS id
"""

# ============================================
# 读侧 Cypher (参数化)
# ============================================

# A. 我与对话对象的全部关系 (可能多条不同 type)
CYPHER_GET_RELATIONS_TO = """
MATCH (me:Entity {id: $speaker_id, world_id: $world_id})
      -[r:RELATES]-(other:Entity {id: $listener_id, world_id: $world_id})
WHERE coalesce(r.confidence, 'medium') <> 'low'
RETURN r.type AS type, max(r.intimacy) AS intimacy,
       collect(DISTINCT r.observer) AS observers, max(r.updated_tick) AS updated_tick
ORDER BY updated_tick DESC
"""

# B. 我记过的全部出边关系 (泛化: 人/物/地点/概念) —— 我的"知识网"
CYPHER_GET_MY_RELATIONS = """
MATCH (me:Entity {id: $speaker_id, world_id: $world_id})-[r:RELATES]-(o:Entity)
WHERE coalesce(r.confidence, 'medium') <> 'low'
RETURN o.name AS name, o.kind AS kind, r.type AS type, max(r.intimacy) AS intimacy,
       collect(DISTINCT r.observer) AS observers, max(r.updated_tick) AS updated_tick
ORDER BY updated_tick DESC, intimacy DESC
LIMIT $limit
"""

# C. 我与对话对象的共同事件
CYPHER_GET_COMMON_EVENTS = """
MATCH (me:Entity {id: $speaker_id, world_id: $world_id})
      -[:PARTICIPATED]->(e:Event)<-[:PARTICIPATED]-
      (other:Entity {id: $listener_id, world_id: $world_id})
WHERE e.world_id = $world_id
RETURN e.description AS description, e.datetime AS datetime, e.tick AS tick
ORDER BY e.tick DESC
LIMIT $limit
"""

# D. 关键词搜实体 (id/name/aliases 含关键词) —— graph_search 工具用
CYPHER_SEARCH_ENTITIES = """
MATCH (e:Entity {world_id: $world_id})
WHERE toLower(e.name) CONTAINS $kw OR toLower(e.id) CONTAINS $kw
   OR ANY(a IN coalesce(e.aliases, []) WHERE toLower(a) CONTAINS $kw)
RETURN e.id AS id, e.name AS name, e.kind AS kind, e.pending AS pending
LIMIT $limit
"""

# E. 给定一组实体 id, 取它们的关系 (排除 low 置信)
CYPHER_SEARCH_RELATIONS = """
MATCH (e:Entity)-[r:RELATES]-(o:Entity)
WHERE e.world_id = $world_id AND e.id IN $ids
  AND coalesce(r.confidence, 'medium') <> 'low'
RETURN startNode(r).name AS subj, r.type AS type, endNode(r).name AS obj,
       endNode(r).kind AS kind, r.observer AS observer, r.confidence AS confidence
LIMIT $limit
"""


# ============================================
# 格式化纯函数 (查询结果 -> 给 LLM 看的紧凑文本)
# ============================================

def format_relations_to(rels, listener_name):
    """格式化「我与对话对象的关系」(查询 A, 多 observer 聚合, 已过滤 low)。

    rels: list[dict] {type, intimacy, observers, updated_tick}
    输出:
        [你与 秘书 的关系]
        - 恋人｜亲密度90｜Alex、David认为
    """
    if not rels:
        return ''
    lines = [f"[你与 {listener_name} 的关系]"]
    for r in rels:
        rtype = r.get('type') or '关系'
        parts = [rtype]
        intimacy = r.get('intimacy')
        if intimacy is not None:
            parts.append(f"亲密度{intimacy}")
        observers = [o for o in (r.get('observers') or []) if o]
        if observers:
            parts.append('、'.join(observers) + '认为')
        lines.append('- ' + '｜'.join(parts))
    return '\n'.join(lines)


def format_my_relations(net):
    """格式化「我记过的关系网」(查询 B, 多 observer 聚合, 已过滤 low)。

    net: list[dict] {name, kind, type, intimacy, observers, updated_tick}
    """
    if not net:
        return ''
    kind_label = {'person': '', 'item': '(物品)', 'place': '(地点)',
                  'topic': '(话题)', 'concept': '(概念)'}
    lines = ['[你记住的关系]']
    for n in net:
        name = n.get('name') or '?'
        kind = n.get('kind') or 'person'
        tag = kind_label.get(kind, f'({kind})') if kind != 'person' else ''
        rtype = n.get('type') or '关系'
        seg = f"- {rtype} {name}{tag}"
        intimacy = n.get('intimacy')
        if intimacy is not None:
            seg += f"（亲密度{intimacy}）"
        observers = [o for o in (n.get('observers') or []) if o]
        if len(observers) > 1:
            seg += f" [{len(observers)}人记]"
        lines.append(seg)
    return '\n'.join(lines)


def format_common_events(events, desc_max=80):
    """格式化共同事件列表 (查询 C)。"""
    if not events:
        return ''
    lines = ['[你们一起经历过]']
    for e in events:
        dt = e.get('datetime') or ''
        desc = (e.get('description') or '').strip()
        if len(desc) > desc_max:
            desc = desc[:desc_max] + '…'
        lines.append(f"- {dt} {desc}".rstrip())
    return '\n'.join(lines)


def format_search_result(ents, rels):
    """格式化关键词搜索结果 (graph_search 工具返回)。

    ents: list[dict] {id, name, kind, pending}
    rels: list[dict] {subj, type, obj, kind, observer, confidence}
    """
    if not ents:
        return ''
    lines = ['匹配实体:']
    for e in ents:
        tag = ' (待确认)' if e.get('pending') else ''
        kind = e.get('kind') or 'person'
        lines.append(f"- {e['name']}({kind}){tag}")
    if rels:
        lines.append('相关关系:')
        for r in rels:
            conf = r.get('confidence') or ''
            conf_tag = f" [{conf}]" if conf and conf != 'high' else ''
            kind = r.get('kind')
            kind_tag = f"({kind})" if kind and kind != 'person' else ''
            lines.append(f"  {r['subj']} -[{r['type']}]-> {r['obj']}{kind_tag}{conf_tag}")
    return '\n'.join(lines)
