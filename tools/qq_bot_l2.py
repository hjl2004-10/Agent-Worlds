# ============================================
# tools/qq_bot_l2.py - QQ通知原子层 (L2)
# 职责: 纯HTTP请求、JSON解析、无状态
# ============================================

"""
QQ Bot 原子层

负责:
1. HTTP 请求发送
2. 响应解析
3. 错误处理

所有函数都是纯函数，无副作用
"""

import urllib.request
import urllib.error
import json

# ========== API 端点 ==========

TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
API_BASE = "https://api.sgroup.qq.com"


# ========== HTTP 工具 ==========

def _http_post(url: str, headers: dict, body: dict) -> dict:
    """
    发送 HTTP POST 请求

    Args:
        url: 请求地址
        headers: 请求头
        body: 请求体

    Returns:
        dict: {"success": bool, "data": ..., "message": str}
    """
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return {"success": True, "data": data}

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        return {"success": False, "message": f"HTTP {e.code}: {error_body}"}

    except urllib.error.URLError as e:
        return {"success": False, "message": f"网络错误: {e.reason}"}

    except Exception as e:
        return {"success": False, "message": f"未知错误: {e}"}


# ========== API 调用 ==========

def fetch_access_token(app_id: str, client_secret: str) -> dict:
    """
    获取 Access Token

    Args:
        app_id: QQ Bot AppID
        client_secret: QQ Bot ClientSecret

    Returns:
        dict: {"success": bool, "data": {"access_token": str, "expires_in": int}}
    """
    result = _http_post(
        TOKEN_URL,
        {},
        {"appId": app_id, "clientSecret": client_secret}
    )

    if result["success"]:
        data = result["data"]
        if "access_token" in data:
            return {"success": True, "data": data}
        else:
            return {"success": False, "message": f"响应格式错误: {data}"}

    return result


# 消息序号计数器
_msg_seq_counter = 1


def post_c2c_message(access_token: str, openid: str, content: str) -> dict:
    """
    发送私聊消息

    Args:
        access_token: Access Token
        openid: 用户 OpenID
        content: 消息内容

    Returns:
        dict: {"success": bool, "data": ..., "message": str}
    """
    global _msg_seq_counter

    url = f"{API_BASE}/v2/users/{openid}/messages"
    headers = {"Authorization": f"QQBot {access_token}"}
    body = {
        "content": content,
        "msg_type": 0,  # 文本消息
        "msg_seq": _msg_seq_counter,
    }

    _msg_seq_counter += 1

    result = _http_post(url, headers, body)

    if result["success"]:
        return {"success": True, "data": result["data"]}

    return result
