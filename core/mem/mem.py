# ============================================
# core/mem/mem.py - 记忆系统总控层
# 职责: 配置持有、接口定义
# ============================================

import core.mem.mem_l1 as l1

# ========== 配置区 ==========
LOG_PATH = "data/individuals"
RAM_BUFFER_SIZE = 20    # RAM缓冲区大小
HDD_HISTORY_SIZE = 50   # HDD历史记录大小


# ========== 接口区 ==========
def remember(npc, content):
    """
    记忆写入
    先写入RAM缓冲, 超限后压缩到HDD
    """
    return l1.write_memory(npc, content, RAM_BUFFER_SIZE, HDD_HISTORY_SIZE)


def recall(npc, count=5):
    """
    记忆读取
    返回最近N条记忆
    """
    return l1.read_memory(npc, count)


def persist(npc, filename):
    """
    持久化记忆到HJL文件
    """
    return l1.persist_memory(npc, filename)
