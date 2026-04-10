# ============================================
# tools/io.py - IO工具总控层
# 职责: 文件读写配置与接口
# ============================================

import os
from pathlib import Path
import tools.io_l1 as l1

# ========== 配置区 ==========
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = str(_PROJECT_ROOT / "data" / "individuals")


# ========== 接口区 ==========
def read_hjl(filepath):
    """
    读取HJL文件

    Args:
        filepath: 文件路径，支持两种格式：
            - "alice.hjl" -> 使用默认 DATA_PATH 前缀
            - "data/worlds/modern/world.hjl" -> 直接使用完整路径
    """
    # 如果路径包含路径分隔符，认为是完整路径
    if "/" in filepath or "\\" in filepath:
        full_path = filepath
    else:
        full_path = f"{DATA_PATH}/{filepath}"
    return l1.load_json_file(full_path)


def write_hjl(filepath, data):
    """
    写入HJL文件

    Args:
        filepath: 文件路径，支持两种格式：
            - "alice.hjl" -> 使用默认 DATA_PATH 前缀
            - "data/worlds/modern/world.hjl" -> 直接使用完整路径
    """
    # 如果路径包含路径分隔符，认为是完整路径
    if "/" in filepath or "\\" in filepath:
        full_path = filepath
    else:
        full_path = f"{DATA_PATH}/{filepath}"

    # 确保目录存在
    dir_path = os.path.dirname(full_path)
    if dir_path:
        l1.ensure_directory(dir_path)

    return l1.save_json_file(full_path, data)


def ensure_data_dir():
    """确保数据目录存在"""
    return l1.ensure_directory(DATA_PATH)
