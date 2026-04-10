# ============================================
# body/npc.py - NPC实体容器
# 职责: 纯数据容器, 仅包含属性, 无方法
# ============================================

from enum import Enum


class WalkMode(str, Enum):
    """行走模式枚举

    继承 str 使得 JSON 序列化时自动变为字符串值，
    前端 API 无需修改即可兼容。
    """
    IDLE = 'idle'
    RANDOM = 'random'
    LINEAR = 'linear'
    TO_TARGET = 'to_target'


class Agent:
    """
    NPC实体 - 纯数据盒子

    行为逻辑不在这里实现：
    - 移动 -> 传给 core/drive
    - 对话 -> 传给 core/social
    - 记忆 -> 传给 core/mem
    """

    def __init__(self, name, x=0, y=0):
        # === 身份标识 ===
        self.name = name
        self.sprite_id = "Adam"      # 精灵图ID (对应 /sprites/{sprite_id}_16x16.png)
        self.world_id = None         # 世界归属 (None = 全局NPC，可在任意世界出现)

        # === 位置坐标 ===
        self.x = x
        self.y = y

        # === 主动性 (话语燃料) ===
        self.initiative = 0
        self.max_initiative = 5              # 主动值上限

        # === 驱动层状态锁 ===
        self.is_talking = False          # 互斥锁: 是否正在对话(禁止移动)
        self.ban_target_uuid = None      # 迟滞锁: 刚聊完的人(禁止再次判定)
        self.god_controlled = False      # 上帝模式: 是否被玩家控制
        self.god_move_direction = None   # 上帝模式: 移动方向 ('up'|'down'|'left'|'right'|None)

        # === 行走状态 ===
        self.walk_mode = WalkMode.IDLE   # 行走模式 (默认静默)
        self.walk_direction = 0.0        # 直线行走方向 (弧度)
        self.walk_mode_tick = 0          # 当前模式已持续的 tick 数
        self.walk_target = None          # 目标坐标 (x, y) 用于 to_target 模式
        self.walk_target_name = None     # 目标地点名称 (用于地点碰撞对话)

        # === 行走配置 (从HJL加载) ===
        self.walk_idle_duration = 80     # 静默状态持续 tick 数 (主要状态)
        self.walk_random_duration = 30   # 随机漫步持续 tick 数
        self.walk_linear_duration = 20   # 直线行走持续 tick 数 (降低，主要靠LLM决定去向)

        # === LLM配置 (从HJL加载) ===
        self.llm_channel = None          # 使用的渠道名称 (None 则用默认)
        self.llm_model = None            # 使用的模型名称 (None 则用默认)

        # === 玩家标识 ===
        self.is_player = False           # 是否为玩家控制 (玩家输入而非LLM)

        # === 启用状态 ===
        self.enabled = True              # 是否启用 (禁用后不参与任何活动)

        # === 微信绑定 ===
        self.wechat_binding = {
            "status": "unbound",         # unbound / qr_pending / bound
            "bot_token": None,
            "ilink_bot_id": None,
            "wechat_uin": None,
        }

        # === 记忆容器 (三层结构) ===
        self.memory = {
            'rom_personality': "",       # 人设描述 (只读)
            'rom_prompt': [],            # 提示词模板数组 (只读，从HJL加载)
            'rom_tools_prompt': "",      # 工具提示 (Skill/MCP 动态生成的摘要)
            'rom_extra_prompt': "",      # 额外提示 (用户手写的教学/指令文本)
            'rom_groups': [],            # 所属群组列表 (动态可变)
            'ram_buffer': [],            # 当前对话缓冲 (易失)
            'ram_tasks': [],             # 任务队列 (易失，系统生成)
            'hdd_history': []            # 长期历史 (持久化)
        }

    def __repr__(self):
        return f"<Agent {self.name} @ ({self.x:.1f},{self.y:.1f}) init={self.initiative}>"
