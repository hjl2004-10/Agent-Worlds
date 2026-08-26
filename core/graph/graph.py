# ============================================
# core/graph/graph.py - 知识图谱总控层
# 职责: 配置持有、driver 单例、生命周期、schema 初始化、session 助手
# ============================================

import json
from pathlib import Path

# 热拔插兼容: 未安装 neo4j 驱动时功能整体静默关闭, 基础存储不受影响
try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

# 配置文件路径 (项目根 / config / graph.json)
_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "graph.json"

# 模块级状态
_driver = None       # neo4j.Driver 单例
_enabled = False     # init 成功才为 True
_config = None       # 缓存的配置 dict


def _load_config():
    """读取 config/graph.json，失败返回 None。"""
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Graph] 读取配置失败 {_CONFIG_PATH}: {e}")
        return None


def get_config():
    """返回缓存的配置 dict (供业务层读限量参数)，未初始化返回 {}。"""
    return _config or {}


def set_config(updates):
    """运行时更新图谱配置 + 持久化到 config/graph.json (前端改完即时生效)。"""
    global _config
    if _config is None:
        _config = {}
    _config.update(updates or {})
    try:
        import json as _json
        with open(_CONFIG_PATH, "w", encoding="utf-8") as _f:
            _json.dump(_config, _f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Graph] 保存配置失败: {e}")
        return False


def is_enabled():
    """图谱功能是否可用 (init 成功且未关闭)。"""
    return _enabled and _driver is not None


def _ensure_schema():
    """建约束与索引 (幂等)。逐条执行，单条失败不中断。"""
    statements = [
        # 节点统一为 :Entity, 旧的 :Character 约束/索引废弃, 清理
        "DROP CONSTRAINT character_id_unique IF EXISTS",
        "DROP INDEX character_world_idx IF EXISTS",
        # 通用实体约束/索引
        "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
        "FOR (e:Entity) REQUIRE (e.id, e.world_id) IS UNIQUE",
        "CREATE CONSTRAINT event_id_unique IF NOT EXISTS "
        "FOR (e:Event) REQUIRE e.id IS UNIQUE",
        "CREATE INDEX entity_world_idx IF NOT EXISTS "
        "FOR (e:Entity) ON (e.world_id)",
        "CREATE INDEX event_world_tick_idx IF NOT EXISTS "
        "FOR (e:Event) ON (e.world_id, e.tick)",
        "CREATE INDEX event_creator_idx IF NOT EXISTS "
        "FOR (e:Event) ON (e.created_by, e.tick)",
        "CREATE INDEX entity_pending_idx IF NOT EXISTS "
        "FOR (e:Entity) ON (e.pending)",
    ]
    with _driver.session() as s:
        for stmt in statements:
            try:
                s.run(stmt)
            except Exception as e:
                # 约束/索引已存在等情况不致命，记录后继续
                print(f"[Graph] schema 语句跳过: {e}")


def init():
    """初始化 driver 并建 schema。

    设计: 任何异常都不向上抛，降级为 _enabled=False，
    保证 Neo4j 不可用时对话主流程不受影响。
    """
    global _driver, _enabled, _config
    cfg = _load_config()
    if cfg is None:
        return
    _config = cfg

    if GraphDatabase is None:
        print("[Graph] 未安装 neo4j 驱动 (pip install neo4j)，图谱功能关闭")
        return

    if not cfg.get("enabled", True):
        print("[Graph] 已在 config 中禁用，功能关闭")
        return

    try:
        _driver = GraphDatabase.driver(
            cfg["uri"],
            auth=(cfg["user"], cfg["password"]),
            connection_timeout=5,
        )
        _driver.verify_connectivity()
        _ensure_schema()
        _enabled = True
        print(f"[Graph] Neo4j 连接成功 ({cfg['uri']})")
    except Exception as e:
        print(f"[Graph] Neo4j 不可用，图谱功能降级为静默关闭: {e}")
        _driver = None
        _enabled = False


def shutdown():
    """关闭 driver。"""
    global _driver, _enabled
    if _driver is not None:
        try:
            _driver.close()
        except Exception:
            pass
    _driver = None
    _enabled = False


# ============================================
# session 助手 (所有读写都经此处，统一降级)
# ============================================

def read(cypher, params=None):
    """执行读查询，返回 list[dict]。未启用或失败返回 []。"""
    if not is_enabled():
        return []
    try:
        with _driver.session() as s:
            return s.run(cypher, params or {}).data()
    except Exception as e:
        print(f"[Graph] read 失败: {e}")
        return []


def write(cypher, params=None):
    """执行单条写查询 (自动提交事务)。成功 True，失败/未启用 False。"""
    if not is_enabled():
        return False
    try:
        with _driver.session() as s:
            s.execute_write(lambda tx: tx.run(cypher, params or {}).consume())
        return True
    except Exception as e:
        print(f"[Graph] write 失败: {e}")
        return False


def write_tx(work):
    """执行多语句原子事务。

    work(tx): 在事务里用 tx.run(...) 跑多条，可返回值。
    返回 work 的返回值；未启用或失败返回 None。
    用于 record_event 这种"建事件+参与边+时序链"需原子的场景。
    """
    if not is_enabled():
        return None
    try:
        with _driver.session() as s:
            return s.execute_write(work)
    except Exception as e:
        print(f"[Graph] write_tx 失败: {e}")
        return None


def ensure_entities(names, world_id):
    """启动时为已知实体(如 NPC)预建正式 entity (pending=false)。

    避免 NPC 名在 relate 时被当陌生名进待归一队列。
    已存在的 pending entity 会被转正式(ON MATCH SET pending=false)。
    """
    if not is_enabled():
        return
    from core.graph import graph_l2
    from env import time as world_time
    now = world_time.get_datetime_str()
    try:
        with _driver.session() as s:
            for name in names:
                nm = (name or '').strip()
                if not nm:
                    continue
                s.run(graph_l2.CYPHER_ENSURE_ENTITY, {
                    'eid': nm.lower(), 'name': nm, 'kind': 'person',
                    'world_id': world_id, 'now': now,
                })
    except Exception as e:
        print(f"[Graph] ensure_entities 失败: {e}")
