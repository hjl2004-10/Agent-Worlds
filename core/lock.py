# ============================================
# core/lock.py - 全局线程锁
# 职责: 保护主循环线程与 FastAPI 线程之间的共享可变状态
# ============================================

import threading

# NPC 列表锁 — 保护 main.npcs 的读写
# 使用 RLock 允许同一线程内嵌套获取（例如 dispatcher 中 find_npc + 遍历）
npcs_lock = threading.RLock()

# 对话状态锁 — 保护 social_l1 中的全局对话状态
conversation_lock = threading.RLock()
