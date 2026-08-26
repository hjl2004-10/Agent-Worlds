# ============================================
# tools/graph_l1.py - 知识图谱工具 handler 层
# 职责: relate / record_event 两个工具的执行入口
#        (工具定义在 tools/tool.py, 这里只写执行逻辑)
# 调 core/graph/graph_l1.py 的写入业务, Neo4j 为唯一存储。
# ============================================


def _tool_relate(input_obj, npc, context):
    """工具 relate: 记一条通用关系到知识图谱。

    主体默认是自己, 可指定第三方 (subject);
    客体可是人/物/地点/概念 (object + object_kind)。
    """
    relation = (input_obj.get("relation") or "").strip()
    if not relation:
        return "错误：缺少 relation（关系类型）"
    object_name = (input_obj.get("object") or "").strip()
    if not object_name:
        return "错误：缺少 object（客体）"

    subject_name = (input_obj.get("subject") or "").strip() or npc.name
    object_kind = (input_obj.get("object_kind") or "person").strip()
    intimacy = input_obj.get("intimacy")  # 可 None
    note = (input_obj.get("note") or "").strip()
    confidence = input_obj.get("confidence")  # 可选, None 则自动推断

    from core.graph import graph_l1
    ok = graph_l1.write_relation(
        recorder=npc, subject_name=subject_name, relation=relation,
        object_name=object_name, object_kind=object_kind,
        intimacy=intimacy, note=note, confidence=confidence,
    )
    if ok:
        return f"已记录关系：{subject_name} -[{relation}]-> {object_name}"
    return "记录失败：知识图谱未就绪"


def _tool_record_event(input_obj, npc, context):
    """工具 record_event: 记录一个事件到经历图谱。

    时间由服务端取, 不暴露给 LLM; 参与者默认含自己和当前对话对象。
    """
    desc = (input_obj.get("description") or "").strip()
    if not desc:
        return "错误：缺少 description"
    if len(desc) > 200:
        return "错误：description 过长（超过200字），请精简到一句事实"

    participants = list(input_obj.get("participants") or [])
    if npc.name not in participants:
        participants.append(npc.name)
    listener = context.get("listener") if context else None
    if listener and listener.name not in participants:
        participants.append(listener.name)

    cause_id = (input_obj.get("cause_event_id") or "").strip() or None
    confidence = input_obj.get("confidence")  # 可选, None 则默认 high

    from core.graph import graph_l1
    eid = graph_l1.write_event(
        recorder=npc, description=desc,
        participants=participants, cause_event_id=cause_id, confidence=confidence,
    )
    if eid:
        return f"已记录事件（id={eid}）"
    return "记录失败：知识图谱未就绪"


def _tool_graph_search(input_obj, npc, context):
    """工具 graph_search: 按关键词搜知识图谱实体+关系 (NPC 主动查找)。

    区别于自动注入的 {graph_relation}/{graph_path}: 这个是 NPC 主动想查证时调用。
    """
    keyword = (input_obj.get("keyword") or "").strip()
    if not keyword:
        return "错误：缺少 keyword"
    limit = input_obj.get("limit") or 10
    from core.graph import graph_l1
    world_id = graph_l1._world_id_of(npc)
    return graph_l1.search_by_keyword(keyword, world_id, limit=limit)
