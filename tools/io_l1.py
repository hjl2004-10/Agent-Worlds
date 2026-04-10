# ============================================
# tools/io_l1.py - IO业务层
# 职责: 文件操作流程、异常处理
# ============================================

import json
import os


def load_json_file(filepath):
    """加载JSON文件并返回字典"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[IO] 文件不存在: {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"[IO] JSON解析失败: {filepath}, {e}")
        return None


def save_json_file(filepath, data):
    """将字典保存为JSON文件"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[IO] 写入失败: {filepath}, {e}")
        return False


def ensure_directory(path):
    """确保目录存在"""
    if not os.path.exists(path):
        os.makedirs(path)
        return True
    return False
