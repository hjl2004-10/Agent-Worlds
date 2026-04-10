# ============================================
# tools/loader.py - NPC加载器总控层
# 职责: 配置持有、接口定义
# ============================================

from pathlib import Path
import tools.loader_l1 as l1

# ========== 配置区 ==========
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = str(_PROJECT_ROOT / "data" / "individuals")


# ========== 接口区 ==========
def load_npc(filename):
    """加载单个NPC"""
    return l1.load_npc_from_file(DATA_PATH, filename)


def load_all_npcs(filenames, world_id=None):
    """批量加载NPC，可选按世界过滤

    Args:
        filenames: 文件名列表
        world_id: 如果指定，只加载属于该世界的NPC
    """
    return l1.load_all_npcs_from_files(DATA_PATH, filenames, world_id)


def load_npcs_for_world(world_id):
    """加载指定世界的NPC (包括全局NPC)

    Args:
        world_id: 世界ID

    Returns:
        list: NPC列表
    """
    # 扫描所有 NPC 文件
    npc_files = [f.name for f in Path(DATA_PATH).glob("*.hjl")]
    return l1.load_all_npcs_from_files(DATA_PATH, npc_files, world_id)


def save_npc(agent, filename):
    """持久化Agent到HJL"""
    return l1.save_npc_to_file(DATA_PATH, agent, filename)
