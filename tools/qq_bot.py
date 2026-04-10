# ============================================
# tools/qq_bot.py - QQ通知总控层 (L0)
# 职责: 配置持有、接口定义
# ============================================

"""
QQ Bot 通知模块

用于向 QQ 用户发送通知消息（单向推送）
不需要 WebSocket，纯 HTTP 调用

配置文件: config/qq_bot.json
"""

import json
from pathlib import Path

# ========== 配置 ==========
# 从 config/qq_bot.json 加载

_config_path = Path(__file__).parent.parent / "config" / "qq_bot.json"
_config = {}

def _load_config():
    """加载配置文件"""
    global _config
    if _config_path.exists():
        with open(_config_path, "r", encoding="utf-8") as f:
            _config = json.load(f)
    return _config

# 启动时加载配置
_load_config()

# 配置访问
APP_ID = _config.get("app_id", "")
CLIENT_SECRET = _config.get("client_secret", "")
ADMIN_OPENID = _config.get("admin_openid", "")
ENABLED = _config.get("enabled", False)


# ========== 接口区 ==========

def send_notify(message: str, target_openid: str = None) -> dict:
    """
    发送 QQ 通知消息

    Args:
        message: 通知内容
        target_openid: 目标用户 openid (None 则发给管理员)

    Returns:
        dict: {"success": bool, "message": str, "data": ...}
    """
    if not ENABLED:
        return {"success": False, "message": "QQ 通知功能未启用"}

    if not APP_ID or not CLIENT_SECRET:
        return {"success": False, "message": "QQ Bot 配置缺失"}

    from tools import qq_bot_l1
    openid = target_openid or ADMIN_OPENID
    return qq_bot_l1.send_c2c_message(message, openid)


def is_configured() -> bool:
    """检查是否已配置"""
    return bool(APP_ID and CLIENT_SECRET and ADMIN_OPENID and ENABLED)


def get_status() -> dict:
    """获取模块状态"""
    return {
        "enabled": ENABLED,
        "configured": is_configured(),
        "admin_openid": ADMIN_OPENID[:8] + "..." if ADMIN_OPENID else None,
    }
