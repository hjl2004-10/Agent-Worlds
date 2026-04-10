# ============================================
# core/wechat/wechat.py - 微信 iLink 总控层
# 职责: 配置持有、接口定义
# ============================================

import core.wechat.wechat_l1 as l1

# ========== 配置区 ==========
ILINK_API_BASE = "https://ilinkai.weixin.qq.com"
POLL_INTERVAL = 3          # 消息轮询间隔 (秒)
BUSY_REPLY = "该角色正在忙碌中，请稍后再试~"
FAREWELL_MSG = "拜拜了，下次再聊~"
TOOL_STATUS_PREFIX = "正在"  # 工具状态前缀


# ========== 接口 ==========

def start_polling():
    """启动微信消息轮询线程 (由 main.py 调用)"""
    l1.start_polling()


def stop_polling():
    """停止轮询"""
    l1.stop_polling()


def bind_npc(npc_name: str):
    """发起 NPC 微信绑定 (获取二维码)

    Returns:
        dict: {qrcode_url, session_key} 或 {error}
    """
    return l1.bind_npc(npc_name)


def get_bind_status(npc_name: str):
    """查询绑定状态

    Returns:
        dict: {status, bot_token?, ilink_bot_id?}
    """
    return l1.get_bind_status(npc_name)


def unbind_npc(npc_name: str):
    """解除 NPC 微信绑定"""
    return l1.unbind_npc(npc_name)


def send_tool_status(npc, tool_name: str, description: str = ""):
    """发送工具调用状态到微信 (由 social_l1 调用)

    只在微信对话中、且本轮尚未发送过状态时才发送。

    Args:
        npc: 正在对话的 NPC
        tool_name: 工具名称
        description: 工具描述 (可选，没有则用 tool_name)
    """
    l1.send_tool_status(npc, tool_name, description)
