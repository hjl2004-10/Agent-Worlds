# ============================================
# core/wechat/wechat_l2.py - 微信 iLink 原子层
# 职责: HTTP 请求封装、消息格式化 (无状态)
# ============================================

import json
import time
import random
import string
import requests


def get_qrcode(api_base: str) -> dict:
    """获取登录二维码

    Returns:
        dict: {qrcode_url, session_key} 或抛异常
    """
    url = f"{api_base}/ilink/bot/get_bot_qrcode"
    resp = requests.get(url, params={"bot_type": 3}, timeout=30)
    data = resp.json()

    if data.get("ret", 0) != 0:
        raise Exception(f"获取二维码失败: {data.get('err_msg', 'unknown')}")

    return {
        "qrcode_url": data.get("qrcode_img_content", ""),
        "session_key": data.get("qrcode", ""),
    }


def poll_qrcode_status(api_base: str, session_key: str) -> dict:
    """轮询二维码扫码状态

    Returns:
        dict: {status, bot_token?, ilink_bot_id?}
        status: pending / scaned / confirmed / expired
    """
    url = f"{api_base}/ilink/bot/get_qrcode_status"
    resp = requests.get(url, params={"qrcode": session_key}, timeout=30)
    data = resp.json()

    result = {"status": data.get("status", "pending")}
    if result["status"] == "confirmed":
        result["bot_token"] = data.get("bot_token", "")
        result["ilink_bot_id"] = data.get("ilink_bot_id", "")
    return result


def get_updates(api_base: str, bot_token: str, wechat_uin: str,
                get_updates_buf: str = None) -> dict:
    """拉取新消息

    Returns:
        dict: {msgs: list, get_updates_buf: str}
    """
    url = f"{api_base}/ilink/bot/getupdates"
    headers = _build_headers(bot_token, wechat_uin)

    body = {"base_info": {"channel_version": "1.0.0"}}
    if get_updates_buf:
        body["get_updates_buf"] = get_updates_buf

    resp = requests.post(url, json=body, headers=headers, timeout=30)
    data = resp.json()

    if data.get("ret") and data["ret"] != 0:
        raise Exception(f"拉取消息失败: {data.get('err_msg', 'unknown')}")

    msgs = []
    for msg in data.get("msgs", []):
        text = _extract_text(msg)
        if text:
            msgs.append({
                "text": text,
                "from_user_id": msg.get("from_user_id", ""),
                "context_token": msg.get("context_token", ""),
            })

    return {
        "msgs": msgs,
        "get_updates_buf": data.get("get_updates_buf", ""),
    }


def send_message(api_base: str, bot_token: str, wechat_uin: str,
                 ilink_bot_id: str, to_user_id: str,
                 context_token: str, text: str) -> bool:
    """发送消息到微信

    Returns:
        bool: 是否成功
    """
    url = f"{api_base}/ilink/bot/sendmessage"
    headers = _build_headers(bot_token, wechat_uin)

    client_id = f"kuafu-{int(time.time())}-{''.join(random.choices(string.ascii_lowercase, k=6))}"

    body = {
        "msg": {
            "from_user_id": ilink_bot_id,
            "to_user_id": to_user_id,
            "client_id": client_id,
            "message_type": 2,
            "message_state": 2,
            "context_token": context_token,
            "item_list": [{
                "type": 1,
                "text_item": {"text": text}
            }]
        },
        "base_info": {"channel_version": "1.0.0"}
    }

    resp = requests.post(url, json=body, headers=headers, timeout=10)
    data = resp.json()

    # ret 为 undefined 或 0 都算成功
    if data.get("ret") and data["ret"] != 0:
        print(f"[WeChat] 发送失败: {data.get('err_msg', 'unknown')}")
        return False
    return True


def clean_markdown(text: str) -> str:
    """清理 Markdown 格式符号，转为纯文本"""
    import re
    # 去除代码块
    text = re.sub(r'```[\s\S]*?```', '', text)
    # 去除行内代码
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 去除粗体/斜体
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    # 去除标题标记
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # 去除链接，保留文字
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    return text.strip()


def generate_wechat_uin() -> str:
    """生成随机 X-WECHAT-UIN"""
    return ''.join(random.choices(string.digits, k=15))


# ========== 内部 ==========

def _build_headers(bot_token: str, wechat_uin: str) -> dict:
    return {
        "Content-Type": "application/json",
        "X-WECHAT-UIN": wechat_uin,
        "Authorization": f"Bearer {bot_token}",
        "AuthorizationType": "ilink_bot_token",
    }


def _extract_text(msg: dict) -> str:
    """从 iLink 消息中提取文本内容"""
    for item in msg.get("item_list", []):
        if item.get("type") == 1:
            text_item = item.get("text_item", {})
            return text_item.get("text", "")
    return ""
