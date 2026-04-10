# ============================================
# tools/qq_bot_l1.py - QQ通知业务层 (L1)
# 职责: Token缓存管理、消息发送流程
# ============================================

"""
QQ Bot 业务层

负责:
1. Access Token 获取与缓存
2. 消息发送流程组装
"""

import time
from tools import qq_bot_l2 as l2
from tools import qq_bot as config

# ========== Token 缓存 ==========

_token_cache = {
    "token": None,
    "expires_at": 0  # 过期时间戳
}


def _get_access_token() -> str:
    """
    获取 Access Token（带缓存）

    Token 有效期约 7200 秒，提前 5 分钟刷新

    Returns:
        str: Access Token

    Raises:
        Exception: 获取失败
    """
    now = time.time()

    # 检查缓存，提前 5 分钟刷新
    if _token_cache["token"] and now < _token_cache["expires_at"] - 300:
        return _token_cache["token"]

    # 获取新 Token
    result = l2.fetch_access_token(config.APP_ID, config.CLIENT_SECRET)

    if not result.get("success"):
        raise Exception(f"获取 Token 失败: {result.get('message')}")

    # 更新缓存
    _token_cache["token"] = result["data"]["access_token"]
    _token_cache["expires_at"] = now + int(result["data"]["expires_in"])

    print(f"[QQ Bot] Token 已更新，有效期 {int(result['data']['expires_in'])} 秒")
    return _token_cache["token"]


def clear_token_cache():
    """清除 Token 缓存"""
    global _token_cache
    _token_cache = {"token": None, "expires_at": 0}
    print("[QQ Bot] Token 缓存已清除")


# ========== 消息发送 ==========

def send_c2c_message(content: str, openid: str) -> dict:
    """
    发送私聊消息

    Args:
        content: 消息内容
        openid: 用户 OpenID

    Returns:
        dict: {"success": bool, "message": str, "data": ...}
    """
    try:
        token = _get_access_token()
        result = l2.post_c2c_message(token, openid, content)

        if result.get("success"):
            print(f"[QQ Bot] 消息已发送至 {openid[:8]}...")
            return {"success": True, "message": "发送成功", "data": result.get("data")}
        else:
            # 如果是 Token 相关错误，清除缓存
            if "token" in result.get("message", "").lower():
                clear_token_cache()
            return result

    except Exception as e:
        return {"success": False, "message": str(e)}
