# ============================================
# core/social/conversation_task.py - 对话任务状态机
# 职责: 将阻塞对话拆为可逐 tick 推进的异步任务
# ============================================

import time
import uuid
import threading
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future

# ========== 配置 ==========
# 最大并发对话数 (所有类型共享: NPC碰撞/定时器/地点/玩家)
# 设为 1 = 和旧版串行行为一致
# 设为 0 = 不限制
MAX_CONCURRENT_CONVERSATIONS = 0

# LLM 调用线程池
_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="llm-conv")


class ConvState(Enum):
    """对话任务状态"""
    INIT = "init"                   # 刚创建，等待启动
    WAIT_PLAYER = "wait_player"     # 等待玩家输入
    WAIT_WECHAT = "wait_wechat"     # 等待微信用户输入
    CALLING_LLM = "calling_llm"     # LLM 正在调用中 (线程池)
    EXEC_TOOLS = "exec_tools"       # 工具执行中 (线程池)
    PROCESS_RESULT = "process_result"  # 处理 LLM/工具结果
    NEXT_TURN = "next_turn"         # 准备下一轮
    FINALIZING = "finalizing"       # 对话结束，写入记忆
    DONE = "done"                   # 完成


class ConvType(Enum):
    """对话类型"""
    NPC_NPC = "npc_npc"         # NPC 碰撞对话
    LOCATION = "location"       # 地点碰撞对话
    TIMER = "timer"             # 定时器触发对话
    WECHAT = "wechat"           # 微信用户对话


class ConversationTask:
    """一个对话任务实例

    通过 tick() 方法逐步推进，不阻塞主线程。
    每次 tick() 检查当前状态，如果可以推进则前进一步。
    """

    def __init__(self, conv_type, npc_a, npc_b=None, **kwargs):
        """
        Args:
            conv_type: ConvType
            npc_a: 主 NPC (碰撞对话的 A 方 / 地点对话的 NPC / 定时器的目标 NPC)
            npc_b: 对方 NPC (碰撞对话的 B 方，地点/定时器为 None)
            kwargs:
                location_name: 地点名 (地点对话)
                timer_desc: 定时器描述 (定时器对话)
        """
        self.id = str(uuid.uuid4())[:8]
        self.conv_type = conv_type
        self.npc_a = npc_a
        self.npc_b = npc_b
        self.state = ConvState.INIT

        # 额外参数
        self.location_name = kwargs.get('location_name')
        self.timer_desc = kwargs.get('timer_desc')
        self.wechat_trigger = kwargs.get('wechat_trigger')  # 微信触发消息

        # 对话进度
        self.round_count = 0
        max_rounds_map = {ConvType.NPC_NPC: 15, ConvType.WECHAT: 15}
        self.max_rounds = max_rounds_map.get(conv_type, 3)
        self.speaker = None
        self.listener = None

        # 异步调用
        self._future = None           # ThreadPoolExecutor Future
        self._pending_response = None  # LLM 返回的文本
        self.cancel_event = threading.Event()  # 取消标志，force_stop 时 set()

        # 时间戳
        self.created_at = time.time()
        self.last_tick_at = time.time()

    @property
    def is_done(self):
        return self.state == ConvState.DONE

    @property
    def involves_player(self):
        if self.npc_a and self.npc_a.is_player:
            return True
        if self.npc_b and self.npc_b.is_player:
            return True
        return False

    @property
    def npc_names(self):
        names = [self.npc_a.name]
        if self.npc_b:
            names.append(self.npc_b.name)
        return names

    def __repr__(self):
        if self.conv_type == ConvType.NPC_NPC:
            return f"<Conv:{self.id} {self.npc_a.name}<->{self.npc_b.name} state={self.state.value} round={self.round_count}>"
        elif self.conv_type == ConvType.LOCATION:
            return f"<Conv:{self.id} {self.npc_a.name}@{self.location_name} state={self.state.value}>"
        elif self.conv_type == ConvType.TIMER:
            return f"<Conv:{self.id} timer->{self.npc_a.name} state={self.state.value}>"
        else:
            return f"<Conv:{self.id} wechat->{self.npc_a.name} state={self.state.value}>"


# ========== 对话管理器 ==========

# 活跃对话列表
_active_tasks = []


def get_active_count():
    """获取当前活跃对话数"""
    return len(_active_tasks)


def get_active_tasks():
    """获取所有活跃对话"""
    return list(_active_tasks)


def is_at_capacity():
    """是否已达到并发上限"""
    if MAX_CONCURRENT_CONVERSATIONS <= 0:
        return False
    return len(_active_tasks) >= MAX_CONCURRENT_CONVERSATIONS


def is_npc_busy(npc_name):
    """检查 NPC 是否正在参与对话"""
    for task in _active_tasks:
        if npc_name in task.npc_names:
            return True
    return False


def get_npc_wechat_task(npc_name):
    """获取 NPC 正在进行的微信对话任务 (用于多轮微信输入注入)"""
    for task in _active_tasks:
        if task.conv_type == ConvType.WECHAT and npc_name in task.npc_names:
            return task
    return None


def create_task(conv_type, npc_a, npc_b=None, **kwargs):
    """创建新对话任务

    Returns:
        ConversationTask or None (如果达到上限或 NPC 正忙)
    """
    # 检查并发上限
    if is_at_capacity():
        return None

    # 检查 NPC 是否已在对话中
    if is_npc_busy(npc_a.name):
        return None
    if npc_b and is_npc_busy(npc_b.name):
        return None

    task = ConversationTask(conv_type, npc_a, npc_b, **kwargs)
    _active_tasks.append(task)

    # 冻结 NPC，并挂载取消标志
    npc_a.is_talking = True
    npc_a.cancel_event = task.cancel_event
    if npc_b:
        npc_b.is_talking = True
        npc_b.cancel_event = task.cancel_event

    return task


def remove_task(task):
    """移除已完成的对话任务，解冻 NPC"""
    if task in _active_tasks:
        _active_tasks.remove(task)

    # 解冻 NPC，清除取消标志
    task.npc_a.is_talking = False
    task.npc_a.cancel_event = None
    if task.npc_b:
        task.npc_b.is_talking = False
        task.npc_b.cancel_event = None


def clear_all():
    """清除所有任务 (世界切换时调用)"""
    for task in list(_active_tasks):
        task.npc_a.is_talking = False
        if task.npc_b:
            task.npc_b.is_talking = False
    _active_tasks.clear()


def force_stop_all():
    """强制停止所有活跃对话 (用户主动停止)

    Returns:
        int: 被停止的任务数
    """
    count = 0
    for task in list(_active_tasks):
        if task.state != ConvState.DONE:
            task.state = ConvState.FINALIZING
            task.cancel_event.set()  # 通知工具链停止
            # 尝试取消进行中的 LLM 调用
            if hasattr(task, '_future') and task._future and not task._future.done():
                task._future.cancel()
            count += 1
            print(f"🛑 [ForceStop] 停止对话: {task.id} ({task.npc_a.name})")
    return count


def submit_to_pool(fn, *args, **kwargs):
    """提交函数到线程池执行

    Returns:
        Future
    """
    return _executor.submit(fn, *args, **kwargs)
