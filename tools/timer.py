# ============================================
# tools/timer.py - 定时器总控层 (L0)
# 职责: 配置持有、数据存储、接口定义
# ============================================

import json
from pathlib import Path
from typing import Dict, List, Optional

# 定时器数据文件路径
LEGACY_TIMER_FILE = Path(__file__).parent.parent / "data" / "tasks" / "timers.hjl"

# 内存缓存
_timer_pool: List[Dict] = []


def _get_timer_file(world_id: Optional[str] = None) -> Path:
    """获取当前世界对应的定时器文件路径。"""
    if world_id is None:
        from env import map as map_module
        world_id = getattr(map_module, "_current_world", None)

    if not world_id:
        return LEGACY_TIMER_FILE

    return Path(__file__).parent.parent / "data" / "worlds" / world_id / "runtime" / "timers.hjl"


def load_timers(world_id: Optional[str] = None):
    """加载定时器池"""
    global _timer_pool
    timer_file = _get_timer_file(world_id)
    _timer_pool = []

    if not timer_file.exists():
        # 兼容旧版单世界数据，只迁移到 modern 世界。
        if world_id == "modern" and LEGACY_TIMER_FILE.exists():
            with open(LEGACY_TIMER_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            _timer_pool = data.get("pool", [])
            save_timers(world_id)
        return

    try:
        with open(timer_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _timer_pool = data.get("pool", [])
        print(f"[Timer] 加载 {len(_timer_pool)} 个定时器")
    except Exception as e:
        print(f"[Timer] 加载失败: {e}")
        _timer_pool = []


def save_timers(world_id: Optional[str] = None):
    """保存定时器池"""
    global _timer_pool
    if world_id is None:
        from env import map as map_module
        world_id = getattr(map_module, "_current_world", None)

    timer_file = _get_timer_file(world_id)
    timer_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "header": {
            "version": "v1.0",
            "type": "TIMER_POOL",
            "world_id": world_id
        },
        "pool": _timer_pool
    }

    try:
        with open(timer_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Timer] 保存失败: {e}")


def create_timer(
    name: str,
    description: str,
    target: str,
    interval_ticks: int,
    max_triggers: int = -1
) -> Dict:
    """
    创建定时器

    Args:
        name: 定时器名称
        description: 触发时的提示内容
        target: 目标 NPC 名称
        interval_ticks: 触发间隔 (tick 数)
        max_triggers: 最大触发次数 (-1 表示无限)

    Returns:
        Dict: 定时器对象
    """
    import uuid

    timer = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "description": description,
        "target": target,
        "interval_ticks": interval_ticks,
        "max_triggers": max_triggers,
        "triggered_count": 0,
        "last_trigger_tick": 0,
        "enabled": True
    }

    return timer


def add_timer(timer: Dict):
    """添加定时器到池中"""
    global _timer_pool
    _timer_pool.append(timer)
    save_timers()
    print(f"[Timer] 添加定时器: {timer['name']} -> {timer['target']}")


def remove_timer(timer_id: str) -> bool:
    """移除定时器"""
    global _timer_pool

    for i, t in enumerate(_timer_pool):
        if t.get("id") == timer_id:
            _timer_pool.pop(i)
            save_timers()
            return True
    return False


def get_timers_for(npc_name: str) -> List[Dict]:
    """获取指定 NPC 的所有定时器"""
    return [
        t for t in _timer_pool
        if t.get("target", "").lower() == npc_name.lower()
    ]


def get_all_timers() -> List[Dict]:
    """获取所有定时器"""
    return _timer_pool.copy()


def update_timer(timer_id: str, updates: Dict) -> bool:
    """更新定时器"""
    global _timer_pool

    for t in _timer_pool:
        if t.get("id") == timer_id:
            t.update(updates)
            save_timers()
            return True
    return False


def increment_trigger(timer_id: str, current_tick: int) -> bool:
    """
    增加触发次数

    Returns:
        bool: 是否还应该继续触发 (False 表示已达上限)
    """
    global _timer_pool

    for t in _timer_pool:
        if t.get("id") == timer_id:
            t["triggered_count"] = t.get("triggered_count", 0) + 1
            t["last_trigger_tick"] = current_tick

            # 检查是否达到上限
            max_triggers = t.get("max_triggers", -1)
            if max_triggers > 0 and t["triggered_count"] >= max_triggers:
                t["enabled"] = False
                save_timers()
                return False

            save_timers()
            return True

    return False
