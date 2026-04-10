# ============================================
# tools/task.py - 任务系统总控层 (L0)
# 职责: 配置、接口定义、全局任务池
# ============================================

import json
from pathlib import Path
from typing import Dict, List, Optional

# 任务状态
TASK_STATUS = ['pending', 'done']

# 持久化文件路径
TASK_DATA_DIR = Path(__file__).parent.parent / 'data' / 'tasks'
LEGACY_TASK_DATA_FILE = TASK_DATA_DIR / 'task_pool.hjl'

# ========== 全局任务池 ==========
# 结构: {target_name: [task1, task2, ...]}
# 线程安全: Python GIL 保护简单的字典操作
TASK_POOL: Dict[str, List[Dict]] = {}


def _get_task_data_file(world_id: Optional[str] = None) -> Path:
    """获取当前世界对应的任务池文件路径。"""
    if world_id is None:
        from env import map as map_module
        world_id = getattr(map_module, "_current_world", None)

    if not world_id:
        return LEGACY_TASK_DATA_FILE

    return Path(__file__).parent.parent / 'data' / 'worlds' / world_id / 'runtime' / 'task_pool.hjl'


# ========== 接口区 ==========

def create_task(hint: str, source: Optional[str] = None, tool_hint: Optional[str] = None) -> Dict:
    """
    创建任务对象

    Args:
        hint: 提示文本，直接展示给 AI (自然语言)
        source: 任务来源 (谁给你的)
        tool_hint: 工具使用指引 (如 "read_file: path=xxx")

    Returns:
        Dict: 任务对象
    """
    return {
        'hint': hint,
        'source': source,
        'tool_hint': tool_hint,
        'status': 'pending',
    }


def add_task_to_pool(target_name: str, task: Dict) -> None:
    """
    添加任务到全局池

    Args:
        target_name: 目标 NPC 名称
        task: 任务对象
    """
    if target_name not in TASK_POOL:
        TASK_POOL[target_name] = []
    TASK_POOL[target_name].append(task)
    save_tasks()


def get_all_tasks() -> Dict[str, List[Dict]]:
    """获取所有 NPC 的任务池"""
    return dict(TASK_POOL)


def get_tasks_for(target_name: str) -> List[Dict]:
    """
    获取指定 NPC 的所有任务

    Args:
        target_name: NPC 名称

    Returns:
        List[Dict]: 任务列表 (引用，可直接修改状态)
    """
    return TASK_POOL.get(target_name, [])


def get_pending_tasks_for(target_name: str) -> List[Dict]:
    """
    获取指定 NPC 的待办任务

    Args:
        target_name: NPC 名称

    Returns:
        List[Dict]: pending 状态的任务列表
    """
    return [t for t in TASK_POOL.get(target_name, []) if t.get('status') == 'pending']


def complete_task_in_pool(target_name: str, hint_contains: str) -> int:
    """
    标记任务为完成

    Args:
        target_name: NPC 名称
        hint_contains: 提示文本包含的内容 (模糊匹配)

    Returns:
        int: 完成的任务数量
    """
    count = 0
    for task in TASK_POOL.get(target_name, []):
        if task.get('status') == 'pending' and hint_contains in task.get('hint', ''):
            task['status'] = 'done'
            count += 1
    if count:
        save_tasks()
    return count


def clear_tasks_for(target_name: str) -> None:
    """
    清除指定 NPC 的所有任务

    Args:
        target_name: NPC 名称
    """
    if target_name in TASK_POOL:
        TASK_POOL[target_name] = []
        save_tasks()


def remove_task_from_pool(target_name: str, hint_contains: str) -> int:
    """
    删除任务 (模糊匹配)

    Args:
        target_name: NPC 名称
        hint_contains: 提示文本包含的内容 (模糊匹配)

    Returns:
        int: 删除的任务数量
    """
    if target_name not in TASK_POOL:
        return 0

    original_len = len(TASK_POOL[target_name])
    TASK_POOL[target_name] = [
        t for t in TASK_POOL[target_name]
        if hint_contains not in t.get('hint', '')
    ]
    deleted = original_len - len(TASK_POOL[target_name])
    if deleted:
        save_tasks()
    return deleted


def clear_pool() -> None:
    """清空整个任务池"""
    TASK_POOL.clear()
    save_tasks()


# ========== 持久化接口 ==========

def save_tasks(world_id: Optional[str] = None) -> None:
    """
    保存任务池到 HJL 文件

    在程序退出时调用
    """
    if world_id is None:
        from env import map as map_module
        world_id = getattr(map_module, "_current_world", None)

    task_file = _get_task_data_file(world_id)
    task_file.parent.mkdir(parents=True, exist_ok=True)

    # HJL 格式
    data = {
        "header": {
            "version": "v1.0",
            "type": "TASK_POOL",
            "world_id": world_id
        },
        "pool": TASK_POOL
    }

    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_tasks(world_id: Optional[str] = None) -> None:
    """
    从 HJL 文件加载任务池

    在程序启动时调用
    """
    task_file = _get_task_data_file(world_id)
    TASK_POOL.clear()

    if not task_file.exists():
        # 兼容旧版单世界数据，只迁移到 modern 世界。
        if world_id == "modern" and LEGACY_TASK_DATA_FILE.exists():
            task_file.parent.mkdir(parents=True, exist_ok=True)
            with open(LEGACY_TASK_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "pool" in data:
                TASK_POOL.update(data["pool"])
            else:
                TASK_POOL.update(data)
            save_tasks(world_id)
        return

    try:
        with open(task_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 兼容新旧格式
            if "pool" in data:
                TASK_POOL.update(data["pool"])
            else:
                # 旧格式直接是 pool
                TASK_POOL.update(data)
    except Exception as e:
        print(f"[Task] 加载任务池失败: {e}")
