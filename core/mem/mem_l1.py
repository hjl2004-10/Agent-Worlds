# ============================================
# core/mem/mem_l1.py - 记忆业务层
# 职责: 个体作用域, 记忆管理流程
# ============================================

import core.mem.mem_l2 as l2
from tools import io
from datetime import datetime


def write_memory(npc, content, ram_limit, hdd_limit):
    """
    记忆写入流程
    1. 格式化记忆条目
    2. 写入RAM缓冲
    3. 检查是否需要压缩到HDD
    """
    # 1. 格式化记忆
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted = l2.format_memory(timestamp, npc.name, content)

    # 2. 写入RAM缓冲
    if 'ram_buffer' not in npc.memory:
        npc.memory['ram_buffer'] = []
    npc.memory['ram_buffer'].append(formatted)

    # 3. 检查RAM是否超限
    if len(npc.memory['ram_buffer']) > ram_limit:
        # 压缩: 将RAM转移到HDD (需要转换格式)
        if 'hdd_history' not in npc.memory:
            npc.memory['hdd_history'] = []

        # 转换并追加到HDD
        converted = []
        for msg in npc.memory['ram_buffer']:
            if isinstance(msg, dict):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                if role == 'assistant':
                    record = f"[对话中] 我说: {content}"
                else:
                    record = f"[对话中] 对方说: {content}"
                converted.append(record)
            else:
                converted.append(msg)
        npc.memory['hdd_history'].extend(converted)

        # 清空RAM
        npc.memory['ram_buffer'] = []

        # HDD超限时裁剪旧记录
        if len(npc.memory['hdd_history']) > hdd_limit:
            npc.memory['hdd_history'] = npc.memory['hdd_history'][-hdd_limit:]

    return True


def read_memory(npc, count):
    """
    记忆读取流程
    优先从RAM读取, 不足则从HDD补充
    """
    ram = npc.memory.get('ram_buffer', [])
    hdd = npc.memory.get('hdd_history', [])

    # 合并记忆, RAM在后(更新)
    all_memory = hdd + ram

    # 返回最近N条
    return all_memory[-count:] if len(all_memory) >= count else all_memory


def persist_memory(npc, filename):
    """
    持久化记忆到HJL文件
    """
    # 先把RAM刷到HDD (需要转换格式)
    ram = npc.memory.get('ram_buffer', [])
    if ram:
        if 'hdd_history' not in npc.memory:
            npc.memory['hdd_history'] = []

        # 检查 ram_buffer 内容格式，如果是 JSON 对象则转换为文本
        converted_records = []
        for msg in ram:
            if isinstance(msg, dict):
                # JSON 格式 -> 转换为文本格式
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                if role == 'assistant':
                    record = f"[对话中] 我说: {content}"
                else:
                    record = f"[对话中] 对方说: {content}"
                converted_records.append(record)
            else:
                # 已经是文本格式，直接使用
                converted_records.append(msg)

        npc.memory['hdd_history'].extend(converted_records)
        npc.memory['ram_buffer'] = []

    header = {
        "uuid": npc.name.lower(),
        "name": npc.name
    }
    # 保留 world_id，避免持久化时丢失世界归属
    if getattr(npc, 'world_id', None) is not None:
        header["world_id"] = npc.world_id

    data = {
        "header": header,
        "position": {
            "x": npc.x,
            "y": npc.y
        },
        "attributes": {
            "description": npc.memory.get('rom_personality', ''),
            "prompt": npc.memory.get('rom_prompt', []),
            "extra_prompt": npc.memory.get('rom_extra_prompt', ''),
            "tools": npc.memory.get('rom_tools', []),
            "groups": npc.memory.get('rom_groups', []),
            "base_initiative": npc.initiative,
            "is_player": getattr(npc, 'is_player', False),
            "sprite": {
                "id": getattr(npc, 'sprite_id', 'Adam')
            },
            "walk": {
                "random_duration": getattr(npc, 'walk_random_duration', 30),
                "linear_duration": getattr(npc, 'walk_linear_duration', 70)
            },
            "llm_config": {
                "channel": getattr(npc, 'llm_channel', None),
                "model": getattr(npc, 'llm_model', None)
            }
        },
        "memory": {
            "history": npc.memory.get('hdd_history', []),
            "note": npc.memory.get('hdd_memory_note', '')
        }
    }

    return io.write_hjl(filename, data)
