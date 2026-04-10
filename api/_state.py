# ============================================
# api/_state.py - 共享状态访问器
# 职责: 提供路由模块对 main.py 全局状态的安全访问
# ============================================

# 由 main.py 在 boot() 时设置
_refs = {
    "npcs": None,          # list[Agent] 引用
    "get_tick": None,      # () -> int
    "get_last_event": None,  # () -> str
    "get_event_history": None,  # () -> list[dict]
    "push_event": None,  # (type, npc, detail) -> None
    "find_npc": None,      # (name: str) -> Agent | None
    "build_npc_config": None,  # (npc) -> dict
    "load_scene_config": None,  # () -> dict
    "reset_world_state": None,  # () -> None
    "reset_scene_runtime": None,  # (scene_data, apply_spawns) -> None
}


def init(refs: dict):
    """由 main.py 调用，注入全局状态引用"""
    _refs.update(refs)


def get_npcs():
    return _refs["npcs"] or []


def get_tick():
    fn = _refs["get_tick"]
    return fn() if fn else 0


def get_last_event():
    fn = _refs["get_last_event"]
    return fn() if fn else ""


def get_event_history():
    fn = _refs["get_event_history"]
    return fn() if fn else []


def push_event(event_type: str, npc: str, detail: str):
    fn = _refs["push_event"]
    if fn:
        fn(event_type, npc, detail)


def find_npc(name: str):
    fn = _refs["find_npc"]
    return fn(name) if fn else None


def build_npc_config(npc):
    fn = _refs["build_npc_config"]
    return fn(npc) if fn else {}


def load_scene_config():
    fn = _refs["load_scene_config"]
    return fn() if fn else {}


def reset_world_state():
    fn = _refs["reset_world_state"]
    if fn:
        fn()


def reset_scene_runtime(scene_data=None, apply_spawns=True):
    fn = _refs["reset_scene_runtime"]
    if fn:
        fn(scene_data, apply_spawns)
