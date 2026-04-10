# ============================================
# tools/mailbox_l1.py - 邮箱系统业务层 (L1)
# 职责: 邮件创建、内容处理、工具实现
# ============================================

import os
import base64
import uuid
import re
import struct
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, TYPE_CHECKING

from tools import mailbox as mailbox_module

# 项目根目录 (绝对路径)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

if TYPE_CHECKING:
    from body.npc import Agent


# ========== 图片格式检测 (替代已移除的 imghdr) ==========

def _detect_image_format(data: bytes) -> Optional[str]:
    """
    检测图片格式 (基于文件头魔数)

    Returns:
        格式字符串: 'png', 'jpeg', 'gif', 'bmp', 'webp' 或 None
    """
    if len(data) < 8:
        return None

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'

    # JPEG: FF D8 FF
    if data[:3] == b'\xff\xd8\xff':
        return 'jpeg'

    # GIF: GIF87a 或 GIF89a
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'

    # BMP: BM
    if data[:2] == b'BM':
        return 'bmp'

    # WebP: RIFF....WEBP
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'

    return None


# ========== 邮件创建 ==========

def create_mail(
    from_npc: str,
    to_player: str,
    title: str,
    content: str,
    content_type: str = "text",
    metadata: Optional[Dict] = None
) -> Dict:
    """
    创建邮件对象

    Args:
        from_npc: 发送者 NPC 名称
        to_player: 接收者玩家名称
        title: 邮件标题
        content: 邮件内容
        content_type: 内容类型 (text/html/image/document)
        metadata: 额外元数据

    Returns:
        邮件对象
    """
    mail_id = f"mail_{int(datetime.now().timestamp() * 1000)}_{uuid.uuid4().hex[:6]}"

    mail = {
        "id": mail_id,
        "from": from_npc,
        "to": to_player,
        "title": title,
        "content": content,
        "content_type": content_type,
        "read": False,
        "starred": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "read_at": None,
        "metadata": metadata or {}
    }

    return mail


def send_mail(
    from_npc: str,
    to_player: str,
    title: str,
    content: str,
    content_type: str = "text",
    metadata: Optional[Dict] = None
) -> Dict:
    """
    发送邮件

    Args:
        from_npc: 发送者 NPC 名称
        to_player: 接收者玩家名称
        title: 邮件标题
        content: 邮件内容
        content_type: 内容类型
        metadata: 额外元数据

    Returns:
        发送结果
    """
    # 验证内容类型
    if content_type not in mailbox_module.CONTENT_TYPES:
        return {"status": "error", "reason": f"不支持的内容类型: {content_type}"}

    # 创建邮件
    mail = create_mail(from_npc, to_player, title, content, content_type, metadata)

    # 添加到收件箱
    result = mailbox_module.add_mail(to_player, mail)

    return result


# ========== 内容处理 ==========

def process_file_reference(file_ref: str, npc_name: str) -> Dict:
    """
    处理文件引用，解析路径类型

    支持格式:
    - workspace:path/to/file  → 工作区文件 (冒号格式)
    - workspace\\path\\to\\file → 工作区文件 (Windows 反斜杠格式)
    - data:path/to/file       → 数据目录文件
    - https://...             → 外部 URL

    Args:
        file_ref: 文件引用字符串
        npc_name: NPC 名称 (用于错误提示)

    Returns:
        {type: "path"|"url", value: ..., error: ...}
    """
    # 统一路径分隔符为 /
    normalized_ref = file_ref.replace("\\", "/")

    if normalized_ref.startswith("workspace:"):
        # workspace: 冒号格式
        relative_path = normalized_ref[len("workspace:"):]
        project_root = str(_PROJECT_ROOT)
        full_path = os.path.join(project_root, "workspace", relative_path)

        if not mailbox_module.is_path_allowed(full_path):
            return {"type": "error", "error": f"路径不在白名单内: {relative_path}"}

        if not os.path.exists(full_path):
            return {"type": "error", "error": f"文件不存在: {relative_path}"}

        return {"type": "path", "value": full_path, "display": f"workspace/{relative_path}"}

    elif normalized_ref.startswith("workspace/"):
        # workspace/ 斜杠格式 (来自反斜杠转换)
        relative_path = normalized_ref[len("workspace/"):]
        project_root = str(_PROJECT_ROOT)
        full_path = os.path.join(project_root, "workspace", relative_path)

        if not mailbox_module.is_path_allowed(full_path):
            return {"type": "error", "error": f"路径不在白名单内: {relative_path}"}

        if not os.path.exists(full_path):
            return {"type": "error", "error": f"文件不存在: {relative_path}"}

        return {"type": "path", "value": full_path, "display": f"workspace/{relative_path}"}

    elif normalized_ref.startswith("data:"):
        # 数据目录路径
        relative_path = normalized_ref[len("data:"):]
        project_root = str(_PROJECT_ROOT)
        full_path = os.path.join(project_root, "data", relative_path)

        if not mailbox_module.is_path_allowed(full_path):
            return {"type": "error", "error": f"路径不在白名单内: {relative_path}"}

        if not os.path.exists(full_path):
            return {"type": "error", "error": f"文件不存在: {relative_path}"}

        return {"type": "path", "value": full_path, "display": f"data/{relative_path}"}

    elif normalized_ref.startswith("http://") or normalized_ref.startswith("https://"):
        # 外部 URL
        return {"type": "url", "value": normalized_ref, "display": normalized_ref}

    else:
        # 尝试作为工作区相对路径 (支持反斜杠)
        project_root = str(_PROJECT_ROOT)
        full_path = os.path.join(project_root, "workspace", normalized_ref)

        if os.path.exists(full_path) and mailbox_module.is_path_allowed(full_path):
            return {"type": "path", "value": full_path, "display": f"workspace/{normalized_ref}"}

        return {"type": "error", "error": f"无法识别的文件引用: {file_ref}"}


def save_image_from_base64(base64_data: str, npc_name: str) -> Dict:
    """
    保存 base64 编码的图片到附件目录

    Args:
        base64_data: base64 编码的图片数据 (可带 data:image/xxx;base64, 前缀)
        npc_name: NPC 名称

    Returns:
        {status: "ok", path: ...} 或 {status: "error", reason: ...}
    """
    try:
        # 解析 base64 数据
        if base64_data.startswith("data:image"):
            # 提取 mime 类型和数据
            match = re.match(r"data:image/(\w+);base64,(.+)", base64_data)
            if not match:
                return {"status": "error", "reason": "无效的 base64 图片格式"}
            ext = match.group(1)
            data = match.group(2)
        else:
            # 假设是纯 base64 数据
            data = base64_data
            ext = "png"  # 默认扩展名

        # 解码
        image_data = base64.b64decode(data)

        # 检查大小
        if len(image_data) > mailbox_module.MAX_IMAGE_SIZE:
            size_mb = len(image_data) / (1024 * 1024)
            return {"status": "error", "reason": f"图片超过 10MB 限制 (当前 {size_mb:.1f}MB)"}

        # 验证图片格式
        img_type = _detect_image_format(image_data)
        if img_type:
            ext = img_type

        # 生成文件名
        filename = f"{npc_name.lower()}_{int(datetime.now().timestamp() * 1000)}.{ext}"
        filepath = os.path.join(mailbox_module.ATTACHMENTS_DIR, filename)

        # 保存文件
        with open(filepath, "wb") as f:
            f.write(image_data)

        return {
            "status": "ok",
            "path": f"data:mailbox/attachments/{filename}",
            "filename": filename
        }

    except Exception as e:
        return {"status": "error", "reason": f"保存图片失败: {str(e)}"}


# ========== 工具处理函数 ==========

def _tool_send_mail(input_obj: dict, npc, context) -> str:
    """
    发送邮件 (NPC 工具)

    参数:
        to_player: 接收者玩家名称 (默认 "player")
        title: 邮件标题
        content: 邮件内容
        content_type: 内容类型 (text/html/image/document) 默认 text

    内容类型说明:
        - text: 纯文本内容
        - html: HTML 内容 (将在沙盒中渲染)
        - image: 图片，content 为图片路径或 URL
        - document: 文档，content 为文档路径
    """
    to_player = input_obj.get("to_player", "player")
    title = input_obj.get("title", "")
    content = input_obj.get("content", "")
    content_type = input_obj.get("content_type", "text")

    if not title:
        return "错误: 缺少邮件标题"

    if not content:
        return "错误: 缺少邮件内容"

    metadata = {}

    # 处理不同内容类型
    if content_type == "image":
        # 图片类型 - 处理路径引用
        result = process_file_reference(content, npc.name)
        if result["type"] == "error":
            return f"错误: {result['error']}"

        if result["type"] == "url":
            metadata["image_url"] = result["value"]
            content = result["value"]
        else:
            # 本地文件，使用 API 路径
            metadata["image_url"] = f"/api/mailbox/file?path={result['display']}"
            metadata["local_path"] = result["display"]
            content = result["display"]

    elif content_type == "document":
        # 文档类型 - 处理路径引用
        result = process_file_reference(content, npc.name)
        if result["type"] == "error":
            return f"错误: {result['error']}"

        # 检测文档格式
        ext = os.path.splitext(result["value"])[1].lower().lstrip(".")
        if ext not in mailbox_module.DOCUMENT_FORMATS:
            supported = ", ".join(mailbox_module.DOCUMENT_FORMATS)
            return f"错误: 不支持的文档格式: {ext} (支持: {supported})"

        # 使用显示名称 (doc/docx -> Word, ppt/pptx -> PPT)
        doc_format = mailbox_module.DOCUMENT_FORMAT_NAMES.get(ext, ext.upper())
        metadata["doc_format"] = doc_format
        metadata["doc_ext"] = ext  # 保留原始扩展名
        metadata["local_path"] = result["display"]
        content = result["display"]

    elif content_type == "html":
        # HTML 类型 - 基本安全检查
        # 移除危险的标签和属性
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',  # 事件处理器
        ]
        safe_content = content
        for pattern in dangerous_patterns:
            safe_content = re.sub(pattern, '', safe_content, flags=re.IGNORECASE | re.DOTALL)
        content = safe_content

    # 发送邮件
    result = send_mail(
        from_npc=npc.name,
        to_player=to_player,
        title=title,
        content=content,
        content_type=content_type,
        metadata=metadata
    )

    if result.get("status") == "ok":
        return f"邮件已发送给 {to_player}: {title}"
    else:
        return f"发送失败: {result.get('reason', '未知错误')}"


def _tool_send_image_mail(input_obj: dict, npc, context) -> str:
    """
    发送图片邮件 (NPC 工具) - 支持直接传入图片数据

    参数:
        to_player: 接收者玩家名称 (默认 "player")
        title: 邮件标题
        image_source: 图片来源 (路径/URL/base64)
        description: 图片描述 (可选)
    """
    to_player = input_obj.get("to_player", "player")
    title = input_obj.get("title", "")
    image_source = input_obj.get("image_source", "")
    description = input_obj.get("description", "")

    if not title:
        return "错误: 缺少邮件标题"

    if not image_source:
        return "错误: 缺少图片来源"

    metadata = {}

    # 判断图片来源类型
    if image_source.startswith("data:image"):
        # Base64 编码的图片
        result = save_image_from_base64(image_source, npc.name)
        if result["status"] != "ok":
            return f"错误: {result['reason']}"
        image_url = f"/api/mailbox/file?path={result['path']}"
        metadata["image_url"] = image_url
        content = result["path"]

    elif image_source.startswith("http://") or image_source.startswith("https://"):
        # 外部 URL
        metadata["image_url"] = image_source
        content = image_source

    else:
        # 文件路径引用
        result = process_file_reference(image_source, npc.name)
        if result["type"] == "error":
            return f"错误: {result['error']}"

        if result["type"] == "url":
            metadata["image_url"] = result["value"]
            content = result["value"]
        else:
            image_url = f"/api/mailbox/file?path={result['display']}"
            metadata["image_url"] = image_url
            metadata["local_path"] = result["display"]
            content = result["display"]

    # 添加描述
    if description:
        metadata["description"] = description

    # 发送邮件
    result = send_mail(
        from_npc=npc.name,
        to_player=to_player,
        title=title,
        content=content,
        content_type="image",
        metadata=metadata
    )

    if result.get("status") == "ok":
        return f"图片邮件已发送给 {to_player}: {title}"
    else:
        return f"发送失败: {result.get('reason', '未知错误')}"


def _tool_send_html_mail(input_obj: dict, npc, context) -> str:
    """
    发送 HTML 应用邮件 (NPC 工具)

    参数:
        to_player: 接收者玩家名称 (默认 "player")
        title: 应用名称 (显示在桌面图标下)
        file_path: HTML 文件路径 (相对于 workspace/htmls/，如: snake.html)
        html_content: HTML 代码内容 (与 file_path 二选一)
        device_mode: 设备模式 (mobile=393x852竖屏, desktop=800x600横屏, 默认 mobile)
    """
    to_player = input_obj.get("to_player", "player")
    title = input_obj.get("title", "")
    file_path = input_obj.get("file_path", "")
    html_content = input_obj.get("html_content", "")
    device_mode = input_obj.get("device_mode", "mobile")

    if not title:
        return "错误: 缺少应用名称"

    # 优先使用 file_path，如果没有则使用 html_content
    if file_path:
        # 从 workspace/htmls/ 目录读取文件
        htmls_dir = _PROJECT_ROOT / "workspace" / "htmls"
        full_path = htmls_dir / file_path

        # 安全检查：防止路径遍历
        try:
            full_path = full_path.resolve()
            if not str(full_path).startswith(str(htmls_dir.resolve())):
                return f"错误: 非法路径: {file_path}"
        except Exception:
            return f"错误: 无效路径: {file_path}"

        if not full_path.exists():
            return f"错误: 文件不存在: workspace/htmls/{file_path}"

        if not full_path.is_file():
            return f"错误: 不是有效文件: {file_path}"

        # 读取文件内容
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            return f"错误: 读取文件失败: {str(e)}"

    elif not html_content:
        return "错误: 必须提供 file_path 或 html_content 其中之一"

    # 验证设备模式
    if device_mode not in ["mobile", "desktop"]:
        device_mode = "mobile"

    # html_app 类型允许完整 JS 执行，安全由 iframe sandbox 属性保障
    safe_content = html_content

    # 元数据 (只记录推荐的设备模式，具体尺寸由前端自适应)
    metadata = {
        "device_mode": device_mode,
    }

    # 如果是从文件读取的，记录文件路径
    if file_path:
        metadata["source_file"] = f"workspace/htmls/{file_path}"

    # 发送邮件 (content_type 使用 html_app)
    result = send_mail(
        from_npc=npc.name,
        to_player=to_player,
        title=title,
        content=safe_content,
        content_type="html_app",
        metadata=metadata
    )

    if result.get("status") == "ok":
        mode_text = "竖屏手机" if device_mode == "mobile" else "横屏电脑"
        source_text = f" (来自 {file_path})" if file_path else ""
        return f"HTML应用已发送给 {to_player}: {title}{source_text} ({mode_text}模式)"
    else:
        return f"发送失败: {result.get('reason', '未知错误')}"

