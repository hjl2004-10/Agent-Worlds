# ============================================
# core/graph/graph_l1.py - 知识图谱业务层
# 职责: 检索编排 (format_graph_text) + 写入编排 (write_relation/write_event)
#        纯流程, 不含 Cypher (在 l2) / 不持有 driver (在 graph)
#
# 通用知识图谱: 关系主体可指定第三方 (不只 NPC 自己),
#               客体可是人/物/地点/概念 (不限于人)。
# ============================================

import hashlib

from core.graph import graph
from core.graph import graph_l2 as l2


def _world_id_of(npc):
    """取 world_id: 优先 NPC 自身归属, 全局 NPC (None) 回落到当前世界。"""
    from env import map as map_module
    return (npc.world_id if npc.world_id else None) or map_module._current_world


def recall_relation(speaker, listener, config=None):
    """情境召回: 我和对话对象的关系 + 共同事件。注入 {graph_relation}。

    无 listener 或未启用返回空串。
    """
    if not graph.is_enabled() or not listener:
        return ''
    gcfg = graph.get_config()
    desc_max = gcfg.get('desc_max_chars', 80)
    sid = speaker.name.lower()
    lid = listener.name.lower()
    world_id = _world_id_of(speaker)
    parts = []

    rels = graph.read(l2.CYPHER_GET_RELATIONS_TO, {
        'speaker_id': sid, 'listener_id': lid, 'world_id': world_id,
    })
    fmt_to = l2.format_relations_to(rels, listener.name)
    if fmt_to:
        parts.append(fmt_to)

    events = graph.read(l2.CYPHER_GET_COMMON_EVENTS, {
        'speaker_id': sid, 'listener_id': lid, 'world_id': world_id,
        'limit': gcfg.get('common_event_limit', 3),
    })
    fmt_ev = l2.format_common_events(events, desc_max=desc_max)
    if fmt_ev:
        parts.append(fmt_ev)

    return '\n'.join(parts).strip()


def recall_path(speaker, config=None):
    """路径召回: 我记过的关系网 (出边, 泛化人/物/概念)。注入 {graph_path}。

    让 NPC 记得"自己知道什么"。未启用返回空串。
    """
    if not graph.is_enabled():
        return ''
    gcfg = graph.get_config()
    sid = speaker.name.lower()
    world_id = _world_id_of(speaker)
    my_rels = graph.read(l2.CYPHER_GET_MY_RELATIONS, {
        'speaker_id': sid, 'world_id': world_id,
        'limit': gcfg.get('relation_overview_limit', 8),
    })
    return l2.format_my_relations(my_rels).strip()


def format_graph_text(speaker, listener, config=None):
    """组合召回 (兼容 {graph_text}): relation + path。

    沿用单变量的旧 NPC 模板用这个; 新模板可用 {graph_relation}/{graph_path} 细分。
    """
    parts = []
    r = recall_relation(speaker, listener, config)
    if r:
        parts.append(r)
    p = recall_path(speaker, config)
    if p:
        parts.append(p)
    text = '\n'.join(parts).strip()
    gcfg = graph.get_config()
    max_total = gcfg.get('graph_text_max_chars', 800)
    if len(text) > max_total:
        text = text[:max_total] + '…'
    return text


def search_by_keyword(keyword, world_id, limit=10):
    """关键词搜图谱 (graph_search 工具用): 返回匹配实体 + 其关系的文本。

    匹配实体的 id/name/aliases 含关键词。NPC 主动调用查"某话题/某人"相关。
    """
    if not graph.is_enabled() or not keyword:
        return ''
    kw = keyword.strip().lower()
    if not kw:
        return ''
    ents = graph.read(l2.CYPHER_SEARCH_ENTITIES, {
        'kw': kw, 'world_id': world_id, 'limit': limit,
    })
    if not ents:
        return f"没找到与'{keyword}'相关的实体"
    ent_ids = [e['id'] for e in ents]
    rels = graph.read(l2.CYPHER_SEARCH_RELATIONS, {
        'ids': ent_ids, 'world_id': world_id, 'limit': limit * 2,
    })
    return l2.format_search_result(ents, rels).strip()


def write_relation(recorder, subject_name, relation, object_name,
                   subject_kind='person', object_kind='person',
                   intimacy=None, note='', confidence=None):
    """写一条通用关系 (主体)-[:RELATES {type,observer}]->(客体)。

    经 engine.resolve_entity 归一主体/客体; 带 observer(记录者) + confidence
    (自动推断: subject==observer → high 亲历, 否则 medium 转述)。
    MERGE 键含 observer → 多 NPC 视角并存不覆盖。
    """
    if not graph.is_enabled():
        return False
    from env import time as world_time
    from core.graph import engine

    world_id = _world_id_of(recorder)
    sid = engine.resolve_entity(subject_name, world_id, subject_kind)
    oid = engine.resolve_entity(object_name, world_id, object_kind)
    observer = recorder.name
    if confidence is None:
        confidence = 'high' if subject_name.strip().lower() == observer.lower() else 'medium'

    return graph.write(l2.CYPHER_WRITE_RELATION, {
        'subject_id': sid, 'subject_name': subject_name, 'subject_kind': subject_kind,
        'object_id': oid, 'object_name': object_name, 'object_kind': object_kind,
        'relation': relation, 'observer': observer, 'confidence': confidence,
        'world_id': world_id,
        'intimacy': intimacy, 'note': note or '',
        'now': world_time.get_datetime_str(),
        'tick': world_time.get_tick(),
    })


def write_event(recorder, description, participants, cause_event_id=None, confidence=None):
    """写入一个事件 + 参与者边 + 时序链 + (可选)因果链。

    多段用 write_tx 保证原子。参与者经 engine 归一。返回 event_id / None。
    """
    if not graph.is_enabled():
        return None
    from env import time as world_time
    from core.graph import engine

    recorder_id = recorder.name.lower()
    world_id = _world_id_of(recorder)
    tick = world_time.get_tick()
    now = world_time.get_datetime_str()
    desc_key = hashlib.md5(description.encode('utf-8')).hexdigest()[:8]
    event_id = f"{recorder_id}:{tick}:{desc_key}"
    if confidence is None:
        confidence = 'high'  # 事件由记录者发起, 默认亲历

    # 参与者经 engine 归一 (id + name), 按 id 去重
    seen = set()
    resolved = []
    for p in participants:
        pid = engine.resolve_entity(p, world_id, 'person')
        if pid not in seen:
            seen.add(pid)
            resolved.append({'id': pid, 'name': (p or '').strip()})

    base_params = {
        'event_id': event_id, 'description': description,
        'world_id': world_id, 'tick': tick, 'now': now,
        'recorder_id': recorder_id, 'participants': resolved,
        'confidence': confidence,
    }
    cause_id = cause_event_id

    def work(tx):
        tx.run(l2.CYPHER_WRITE_EVENT, base_params).consume()
        tx.run(l2.CYPHER_LINK_NEXT, {
            'recorder_id': recorder_id, 'world_id': world_id,
            'event_id': event_id, 'tick': tick,
        }).consume()
        if cause_id:
            tx.run(l2.CYPHER_LINK_CAUSED, {
                'cause_id': cause_id, 'event_id': event_id,
            }).consume()
        return event_id

    return graph.write_tx(work)
