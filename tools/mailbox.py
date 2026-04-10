# ============================================
# tools/mailbox.py - 邮箱系统总控层 (L0)
# 职责: 配置持有、接口定义、数据池管理
# ============================================

import json
import os
import time
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# ========== 配置 ==========

# 项目根目录 (使用绝对路径，和 task.py/timer.py 保持一致)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 数据存储路径
MAILBOX_DIR = str(_PROJECT_ROOT / "data" / "mailbox")
INBOX_DIR = str(_PROJECT_ROOT / "data" / "mailbox" / "inbox")
ATTACHMENTS_DIR = str(_PROJECT_ROOT / "data" / "mailbox" / "attachments")

# 邮件数量上限
MAX_MAILS_PER_INBOX = 20

# 图片大小上限 (10MB)
MAX_IMAGE_SIZE = 10 * 1024 * 1024

# 文件访问白名单目录
ALLOWED_PATHS = [
    str(_PROJECT_ROOT / "workspace"),
    str(_PROJECT_ROOT / "data"),
]

# 支持的内容类型 (html_app 为独立应用类型，通过 send_html_mail 工具发送)
CONTENT_TYPES = ["text", "image", "document", "html_app"]

# 支持的文档格式 (文件扩展名)
DOCUMENT_FORMATS = ["pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "md", "csv", "json", "xml", "rtf"]

# 文档格式显示名称映射
DOCUMENT_FORMAT_NAMES = {
    "pdf": "PDF",
    "doc": "Word",
    "docx": "Word",
    "ppt": "PPT",
    "pptx": "PPT",
    "xls": "Excel",
    "xlsx": "Excel",
    "txt": "TXT",
    "md": "Markdown",
    "csv": "CSV",
    "json": "JSON",
    "xml": "XML",
    "rtf": "RTF",
}


# ========== 数据池 ==========

# 内存中的收件箱缓存 {player_name: [mails]}
_inbox_cache: Dict[str, List[Dict]] = {}

# 未读计数缓存 {player_name: unread_count}
_unread_cache: Dict[str, int] = {}


# ========== 初始化 ==========

def init():
    """初始化邮箱系统"""
    # 创建目录
    os.makedirs(INBOX_DIR, exist_ok=True)
    os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
    print("[Mailbox] 初始化完成")


def load_inbox(player_name: str) -> List[Dict]:
    """
    加载玩家的收件箱

    Args:
        player_name: 玩家名称

    Returns:
        邮件列表
    """
    inbox_path = os.path.join(INBOX_DIR, f"{player_name.lower()}.json")

    if not os.path.exists(inbox_path):
        return []

    try:
        with open(inbox_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("mails", [])
    except Exception as e:
        print(f"[Mailbox] 加载收件箱失败: {e}")
        return []


def save_inbox(player_name: str, mails: List[Dict]) -> bool:
    """
    保存玩家的收件箱

    Args:
        player_name: 玩家名称
        mails: 邮件列表

    Returns:
        是否成功
    """
    inbox_path = os.path.join(INBOX_DIR, f"{player_name.lower()}.json")

    try:
        data = {
            "version": "1.0",
            "player": player_name,
            "mails": mails,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(inbox_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Mailbox] 保存收件箱失败: {e}")
        return False


# ========== 接口函数 ==========

def get_inbox(player_name: str) -> List[Dict]:
    """
    获取玩家收件箱 (带缓存)

    Args:
        player_name: 玩家名称

    Returns:
        邮件列表
    """
    if player_name not in _inbox_cache:
        _inbox_cache[player_name] = load_inbox(player_name)
        # 计算未读数
        _unread_cache[player_name] = sum(1 for m in _inbox_cache[player_name] if not m.get("read", False))

    return _inbox_cache[player_name]


def get_unread_count(player_name: str) -> int:
    """
    获取未读邮件数

    Args:
        player_name: 玩家名称

    Returns:
        未读数量
    """
    if player_name not in _unread_cache:
        get_inbox(player_name)  # 触发缓存加载

    return _unread_cache.get(player_name, 0)


def add_mail(player_name: str, mail: Dict) -> Dict:
    """
    添加邮件到收件箱

    Args:
        player_name: 玩家名称
        mail: 邮件对象

    Returns:
        操作结果
    """
    mails = get_inbox(player_name)

    # 检查数量上限
    if len(mails) >= MAX_MAILS_PER_INBOX:
        # 删除最旧的已读邮件
        read_mails = [m for m in mails if m.get("read", False)]
        if read_mails:
            oldest = min(read_mails, key=lambda x: x.get("created_at", ""))
            mails.remove(oldest)
        else:
            return {"status": "error", "reason": "收件箱已满"}

    # 添加邮件
    mails.insert(0, mail)  # 新邮件在最前面

    # 更新缓存和持久化
    _inbox_cache[player_name] = mails
    _unread_cache[player_name] = _unread_cache.get(player_name, 0) + 1
    save_inbox(player_name, mails)

    return {"status": "ok", "mail_id": mail.get("id")}


def mark_as_read(player_name: str, mail_id: str) -> bool:
    """
    标记邮件为已读

    Args:
        player_name: 玩家名称
        mail_id: 邮件ID

    Returns:
        是否成功
    """
    mails = get_inbox(player_name)

    for mail in mails:
        if mail.get("id") == mail_id:
            if not mail.get("read", False):
                mail["read"] = True
                mail["read_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                _unread_cache[player_name] = max(0, _unread_cache.get(player_name, 0) - 1)
                save_inbox(player_name, mails)
            return True

    return False


def mark_all_as_read(player_name: str) -> int:
    """
    标记所有邮件为已读

    Args:
        player_name: 玩家名称

    Returns:
        标记的邮件数量
    """
    mails = get_inbox(player_name)
    count = 0

    for mail in mails:
        if not mail.get("read", False):
            mail["read"] = True
            mail["read_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            count += 1

    _unread_cache[player_name] = 0
    save_inbox(player_name, mails)

    return count


def delete_mail(player_name: str, mail_id: str) -> bool:
    """
    删除邮件

    Args:
        player_name: 玩家名称
        mail_id: 邮件ID

    Returns:
        是否成功
    """
    mails = get_inbox(player_name)

    for i, mail in enumerate(mails):
        if mail.get("id") == mail_id:
            if not mail.get("read", False):
                _unread_cache[player_name] = max(0, _unread_cache.get(player_name, 0) - 1)
            mails.pop(i)
            save_inbox(player_name, mails)
            return True

    return False


def toggle_star(player_name: str, mail_id: str) -> bool:
    """
    切换星标状态

    Args:
        player_name: 玩家名称
        mail_id: 邮件ID

    Returns:
        新的星标状态
    """
    mails = get_inbox(player_name)

    for mail in mails:
        if mail.get("id") == mail_id:
            mail["starred"] = not mail.get("starred", False)
            save_inbox(player_name, mails)
            return mail["starred"]

    return False


def refresh_cache(player_name: str):
    """
    刷新缓存

    Args:
        player_name: 玩家名称
    """
    if player_name in _inbox_cache:
        del _inbox_cache[player_name]
    if player_name in _unread_cache:
        del _unread_cache[player_name]


def is_path_allowed(path: str) -> bool:
    """
    检查路径是否在白名单内

    Args:
        path: 要检查的路径

    Returns:
        是否允许访问
    """
    abs_path = os.path.abspath(path)

    for allowed in ALLOWED_PATHS:
        allowed_abs = os.path.abspath(allowed)
        if abs_path.startswith(allowed_abs):
            return True

    return False
