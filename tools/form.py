# ============================================
# tools/form.py - 表单系统总控层 (L0)
# 职责: 配置持有、内存存储、接口定义
# ============================================

import time
import uuid
from typing import Dict, List, Optional
from datetime import datetime

# ========== 配置 ==========

# 表单超时时间 (秒)
FORM_TIMEOUT = 300  # 5分钟

# 表单字段类型
FIELD_TYPES = ["text", "textarea", "select", "multiselect", "number", "checkbox"]

# ========== 内存存储 ==========

# 待处理的表单 {form_id: form_data}
_pending_forms: Dict[str, Dict] = {}

# 表单响应 {form_id: response_data}
_form_responses: Dict[str, Dict] = {}

# 表单状态: pending -> submitted/expired
_form_status: Dict[str, str] = {}


# ========== 接口函数 ==========

def create_form(
    title: str,
    description: str,
    fields: List[Dict],
    from_npc: str = "系统",
    timeout: int = FORM_TIMEOUT
) -> Dict:
    """
    创建待填写的表单

    Args:
        title: 表单标题
        description: 表单描述
        fields: 字段列表 [{"name": "field1", "label": "字段1", "type": "text", "required": True, ...}]
        from_npc: 发起者 NPC 名称
        timeout: 超时时间 (秒)

    Returns:
        表单对象
    """
    form_id = str(uuid.uuid4())[:8]

    form = {
        "id": form_id,
        "title": title,
        "description": description,
        "fields": fields,
        "from_npc": from_npc,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timeout": timeout,
        "expires_at": time.time() + timeout
    }

    _pending_forms[form_id] = form
    _form_status[form_id] = "pending"

    return form


def get_pending_forms() -> List[Dict]:
    """
    获取所有待处理的表单 (排除已过期的)

    Returns:
        待处理表单列表
    """
    current_time = time.time()
    valid_forms = []

    for form_id, form in list(_pending_forms.items()):
        # 检查是否过期
        if form.get("expires_at", 0) < current_time:
            _form_status[form_id] = "expired"
            if form_id in _pending_forms:
                del _pending_forms[form_id]
            continue

        if _form_status.get(form_id) == "pending":
            valid_forms.append(form)

    # 按创建时间排序 (最新的在前)
    valid_forms.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return valid_forms


def get_form(form_id: str) -> Optional[Dict]:
    """
    获取指定表单

    Args:
        form_id: 表单ID

    Returns:
        表单对象或 None
    """
    form = _pending_forms.get(form_id)
    if form:
        # 检查是否过期
        if form.get("expires_at", 0) < time.time():
            _form_status[form_id] = "expired"
            del _pending_forms[form_id]
            return None
    return form


def submit_form(form_id: str, response: Dict) -> Dict:
    """
    提交表单响应

    Args:
        form_id: 表单ID
        response: 响应数据 {"field_name": "value", ...}

    Returns:
        操作结果
    """
    if form_id not in _pending_forms:
        return {"status": "error", "reason": "表单不存在或已过期"}

    form = _pending_forms[form_id]

    # 检查是否过期
    if form.get("expires_at", 0) < time.time():
        _form_status[form_id] = "expired"
        del _pending_forms[form_id]
        return {"status": "error", "reason": "表单已过期"}

    # 检查必填字段
    for field in form.get("fields", []):
        field_name = field.get("name")
        if field.get("required", False) and field_name not in response:
            return {"status": "error", "reason": f"缺少必填字段: {field.get('label', field_name)}"}

    # 保存响应
    response_data = {
        "form_id": form_id,
        "form_title": form.get("title"),
        "response": response,
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    _form_responses[form_id] = response_data
    _form_status[form_id] = "submitted"

    # 从待处理列表移除
    del _pending_forms[form_id]

    return {"status": "ok", "message": "表单已提交"}


def get_response(form_id: str, wait: bool = True, timeout: int = 300) -> Optional[Dict]:
    """
    获取表单响应 (阻塞式)

    Args:
        form_id: 表单ID
        wait: 是否等待响应
        timeout: 等待超时 (秒)

    Returns:
        响应数据或 None
    """
    import threading

    if form_id not in _form_status:
        return None

    if not wait:
        return _form_responses.get(form_id)

    # 阻塞等待
    start_time = time.time()
    while time.time() - start_time < timeout:
        # 检查是否有响应
        if form_id in _form_responses:
            return _form_responses[form_id]

        # 检查是否过期或被取消
        status = _form_status.get(form_id)
        if status in ["expired", "cancelled"]:
            return None

        # 短暂休眠避免 CPU 占用
        time.sleep(0.5)

    return None


def cancel_form(form_id: str) -> bool:
    """
    取消表单

    Args:
        form_id: 表单ID

    Returns:
        是否成功
    """
    if form_id in _pending_forms:
        del _pending_forms[form_id]
        _form_status[form_id] = "cancelled"
        return True
    return False


def cleanup_expired():
    """清理过期的表单"""
    current_time = time.time()
    expired_ids = []

    for form_id, form in _pending_forms.items():
        if form.get("expires_at", 0) < current_time:
            expired_ids.append(form_id)

    for form_id in expired_ids:
        del _pending_forms[form_id]
        _form_status[form_id] = "expired"

    return len(expired_ids)


def get_pending_count() -> int:
    """获取待处理表单数量"""
    return len(get_pending_forms())
