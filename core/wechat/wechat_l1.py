# ============================================
# core/wechat/wechat_l1.py - 微信 iLink 业务层
# 职责: 消息轮询、NPC 匹配、对话触发、回复推送
# ============================================

import time
import threading
from collections import deque

import core.wechat.wechat_l2 as l2
from core.wechat import wechat as config_module

# ========== 内部状态 ==========
_poll_thread = None
_poll_running = False

# 全局状态锁 — 保护 _bindings, _wechat_contexts, _wechat_input_queue 的并发读写
_state_lock = threading.RLock()

# NPC 绑定信息缓存: {npc_name: {bot_token, ilink_bot_id, wechat_uin, get_updates_buf}}
_bindings = {}

# 二维码会话: {npc_name: {session_key, created_at}}
_qr_sessions = {}

# 微信对话上下文: {npc_name: {from_user_id, context_token, wechat_status_sent}}
_wechat_contexts = {}

# 微信输入队列: {npc_name: deque([text, ...])}  — 用 deque 避免消息覆盖
_wechat_input_queue = {}


# ========== 绑定流程 ==========

def bind_npc(npc_name: str) -> dict:
    """发起绑定: 获取二维码"""
    from api._state import find_npc
    npc = find_npc(npc_name)
    if not npc:
        return {"error": f"NPC '{npc_name}' 不存在"}

    with _state_lock:
        # 防止重复扫码: 检查是否已有进行中的 QR 会话
        if npc_name in _qr_sessions:
            elapsed = time.time() - _qr_sessions[npc_name]["created_at"]
            if elapsed < 180:  # 3分钟内的会话视为有效
                return {"error": f"{npc_name} 已有扫码进行中，请先完成或等待过期"}

    api_base = config_module.ILINK_API_BASE
    try:
        qr = l2.get_qrcode(api_base)
        with _state_lock:
            _qr_sessions[npc_name] = {
                "session_key": qr["session_key"],
                "created_at": time.time(),
            }
        # 启动扫码轮询线程
        t = threading.Thread(
            target=_poll_qr_status,
            args=(npc_name, qr["session_key"]),
            daemon=True,
        )
        t.start()

        return {
            "status": "qr_pending",
            "qrcode_url": qr["qrcode_url"],
            "session_key": qr["session_key"],
        }
    except Exception as e:
        return {"error": str(e)}


def _poll_qr_status(npc_name: str, session_key: str):
    """轮询二维码状态直到确认或过期"""
    api_base = config_module.ILINK_API_BASE
    max_attempts = 90

    for _ in range(max_attempts):
        time.sleep(2)
        # 检查会话是否还在 (可能被取消或被新会话替换)
        with _state_lock:
            if npc_name not in _qr_sessions:
                return
            if _qr_sessions[npc_name]["session_key"] != session_key:
                return  # 被新的扫码会话替换了

        try:
            result = l2.poll_qrcode_status(api_base, session_key)
            status = result["status"]

            if status == "confirmed":
                with _state_lock:
                    # 绑定去重: 同一微信号绑新 NPC 时，自动解绑旧 NPC
                    new_bot_id = result["ilink_bot_id"]
                    for existing_npc, existing_binding in list(_bindings.items()):
                        if existing_npc != npc_name and existing_binding["ilink_bot_id"] == new_bot_id:
                            print(f"[WeChat] ⚠️ 该微信账号已绑定 {existing_npc}，自动解绑旧 NPC")
                            _bindings.pop(existing_npc, None)
                            _wechat_contexts.pop(existing_npc, None)
                            _wechat_input_queue.pop(existing_npc, None)
                            # 清除旧 NPC 的绑定属性
                            from api._state import find_npc as _find
                            old_npc = _find(existing_npc)
                            if old_npc:
                                old_npc.wechat_binding = {"status": "unbound"}
                            break

                    # 绑定成功
                    wechat_uin = l2.generate_wechat_uin()
                    binding = {
                        "bot_token": result["bot_token"],
                        "ilink_bot_id": new_bot_id,
                        "wechat_uin": wechat_uin,
                        "get_updates_buf": "",
                    }
                    _bindings[npc_name] = binding
                    _qr_sessions.pop(npc_name, None)

                # 写入 NPC 属性 (锁外操作，避免死锁)
                from api._state import find_npc
                npc = find_npc(npc_name)
                if npc:
                    npc.wechat_binding = {
                        "bot_token": result["bot_token"],
                        "ilink_bot_id": new_bot_id,
                        "wechat_uin": wechat_uin,
                        "status": "bound",
                    }

                print(f"[WeChat] {npc_name} 绑定成功 (bot_id={new_bot_id})")

                # 推送事件到前端
                try:
                    from api._state import push_event
                    push_event("wechat_bind", npc_name, f"{npc_name} 微信绑定成功")
                except Exception:
                    pass
                return

            elif status == "expired":
                with _state_lock:
                    _qr_sessions.pop(npc_name, None)
                print(f"[WeChat] {npc_name} 二维码已过期")
                return

        except Exception as e:
            print(f"[WeChat] 轮询二维码状态失败: {e}")

    # 超时
    with _state_lock:
        _qr_sessions.pop(npc_name, None)
    print(f"[WeChat] {npc_name} 二维码轮询超时")


def get_bind_status(npc_name: str) -> dict:
    """获取绑定状态"""
    with _state_lock:
        # 检查是否正在扫码
        if npc_name in _qr_sessions:
            return {"status": "qr_pending"}

        # 检查是否已绑定
        if npc_name in _bindings:
            return {
                "status": "bound",
                "ilink_bot_id": _bindings[npc_name]["ilink_bot_id"],
            }

    # 检查 NPC 属性 (锁外)
    from api._state import find_npc
    npc = find_npc(npc_name)
    if npc and hasattr(npc, 'wechat_binding'):
        wb = npc.wechat_binding
        if wb and wb.get("status") == "bound":
            # 从 NPC 属性恢复到内存缓存
            with _state_lock:
                _bindings[npc_name] = {
                    "bot_token": wb["bot_token"],
                    "ilink_bot_id": wb["ilink_bot_id"],
                    "wechat_uin": wb["wechat_uin"],
                    "get_updates_buf": "",
                }
            return {"status": "bound", "ilink_bot_id": wb["ilink_bot_id"]}

    return {"status": "unbound"}


def unbind_npc(npc_name: str) -> dict:
    """解除绑定 (会检查对话状态)"""
    from core.social.conversation_task import get_npc_wechat_task

    # 安全检查: 对话中不允许解绑
    wechat_task = get_npc_wechat_task(npc_name)
    if wechat_task:
        return {"error": f"{npc_name} 正在微信对话中，请等对话结束后再解绑"}

    with _state_lock:
        _bindings.pop(npc_name, None)
        _qr_sessions.pop(npc_name, None)
        _wechat_contexts.pop(npc_name, None)
        _wechat_input_queue.pop(npc_name, None)

    from api._state import find_npc
    npc = find_npc(npc_name)
    if npc and hasattr(npc, 'wechat_binding'):
        npc.wechat_binding = {"status": "unbound"}

    print(f"[WeChat] {npc_name} 已解除绑定")
    return {"status": "unbound"}


# ========== 消息轮询 ==========

def start_polling():
    """启动消息轮询线程"""
    global _poll_thread, _poll_running

    if _poll_running:
        return

    _poll_running = True
    _poll_thread = threading.Thread(target=_poll_loop, daemon=True, name="wechat-poll")
    _poll_thread.start()
    print("[WeChat] 消息轮询已启动")


def stop_polling():
    """停止轮询"""
    global _poll_running
    _poll_running = False
    print("[WeChat] 消息轮询已停止")


def _poll_loop():
    """消息轮询主循环"""
    global _poll_running

    while _poll_running:
        try:
            _poll_all_bindings()
        except Exception as e:
            print(f"[WeChat] 轮询异常: {e}")

        time.sleep(config_module.POLL_INTERVAL)


def _poll_all_bindings():
    """遍历所有绑定的 NPC，拉取新消息"""
    api_base = config_module.ILINK_API_BASE

    with _state_lock:
        bindings_snapshot = list(_bindings.items())

    for npc_name, binding in bindings_snapshot:
        try:
            result = l2.get_updates(
                api_base,
                binding["bot_token"],
                binding["wechat_uin"],
                binding.get("get_updates_buf"),
            )

            # 更新 buf
            if result.get("get_updates_buf"):
                with _state_lock:
                    if npc_name in _bindings:
                        _bindings[npc_name]["get_updates_buf"] = result["get_updates_buf"]

            # 处理消息
            for msg in result.get("msgs", []):
                _handle_incoming_message(npc_name, msg)

        except Exception as e:
            print(f"[WeChat] {npc_name} 拉取消息失败: {e}")


def _handle_incoming_message(npc_name: str, msg: dict):
    """处理一条微信消息"""
    from api._state import find_npc
    from core.social.conversation_task import is_npc_busy, get_npc_wechat_task

    text = msg["text"]
    from_user_id = msg["from_user_id"]
    context_token = msg["context_token"]

    print(f"[WeChat] {npc_name} 收到消息: {text[:50]}...")

    npc = find_npc(npc_name)
    if not npc:
        print(f"[WeChat] NPC '{npc_name}' 不存在，忽略消息")
        return

    # 保存微信上下文 (无论忙不忙都更新，用于回复)
    with _state_lock:
        _wechat_contexts[npc_name] = {
            "from_user_id": from_user_id,
            "context_token": context_token,
            "wechat_status_sent": False,
        }

    # 停止指令检测: 用户发"停止"等关键词立即中断对话
    STOP_KEYWORDS = {"停止", "stop", "结束", "算了", "不做了", "停", "取消"}
    if text.strip().lower() in STOP_KEYWORDS:
        from core.social.conversation_task import force_stop_all
        count = force_stop_all()
        _send_to_wechat(npc_name, f"好的，已停止所有工作。(停止了 {count} 个对话)")
        print(f"[WeChat] 用户发送停止指令，停止了 {count} 个对话")
        return

    # 情况1: NPC 正在微信对话中 → 注入为多轮输入
    wechat_task = get_npc_wechat_task(npc_name)
    if wechat_task:
        set_wechat_input(npc_name, text)
        print(f"[WeChat] {npc_name} 微信多轮输入: {text[:30]}...")
        return

    # 情况2: NPC 在其他对话中 (NPC对话/玩家对话等) → 忙碌
    if npc.is_talking or is_npc_busy(npc_name):
        _send_to_wechat(npc_name, config_module.BUSY_REPLY)
        print(f"[WeChat] {npc_name} 忙碌中，已回复忙碌消息")
        return

    # 情况3: NPC 空闲 → 触发微信对话
    _start_wechat_conversation(npc, text)


def _start_wechat_conversation(npc, trigger_text: str):
    """触发微信对话"""
    from core.social import social

    task = social.start_wechat_conversation(npc, trigger_text)
    if task:
        print(f"[WeChat] 已为 {npc.name} 创建微信对话任务")
    else:
        # 创建失败 (可能在创建过程中被抢占)
        _send_to_wechat(npc.name, config_module.BUSY_REPLY)


# ========== 微信输入 (对话中) ==========

def set_wechat_input(npc_name: str, text: str):
    """追加微信输入到队列 (不会覆盖之前的消息)"""
    with _state_lock:
        if npc_name not in _wechat_input_queue:
            _wechat_input_queue[npc_name] = deque()
        _wechat_input_queue[npc_name].append(text)


def pop_wechat_input(npc_name: str) -> str:
    """弹出最早的微信输入 (FIFO)"""
    with _state_lock:
        q = _wechat_input_queue.get(npc_name)
        if q:
            return q.popleft()
        return None


# ========== 发送消息 ==========

def send_npc_reply(npc_name: str, text: str):
    """NPC 回复推送到微信 (由 social_l1 调用)"""
    # 清理 Markdown
    clean_text = l2.clean_markdown(text)
    _send_to_wechat(npc_name, clean_text)


def send_farewell(npc_name: str):
    """发送告别消息"""
    _send_to_wechat(npc_name, config_module.FAREWELL_MSG)
    print(f"[WeChat] {npc_name} 发送告别消息")


def send_tool_status(npc, tool_name: str, description: str = ""):
    """发送工具调用状态提示

    一轮对话只发一次。
    """
    npc_name = npc.name
    with _state_lock:
        ctx = _wechat_contexts.get(npc_name)
        if not ctx:
            return

        # 已经发过状态提示了，不再发
        if ctx.get("wechat_status_sent"):
            return
        ctx["wechat_status_sent"] = True

    desc = description or tool_name
    status_text = f"[{config_module.TOOL_STATUS_PREFIX}{desc[:20]}...]"
    _send_to_wechat(npc_name, status_text)


def reset_tool_status(npc_name: str):
    """重置工具状态标记 (每轮对话开始时调用)"""
    with _state_lock:
        ctx = _wechat_contexts.get(npc_name)
        if ctx:
            ctx["wechat_status_sent"] = False


def _send_to_wechat(npc_name: str, text: str):
    """底层发送"""
    with _state_lock:
        binding = _bindings.get(npc_name)
        ctx = _wechat_contexts.get(npc_name)

    if not binding or not ctx:
        return

    api_base = config_module.ILINK_API_BASE
    try:
        l2.send_message(
            api_base,
            binding["bot_token"],
            binding["wechat_uin"],
            binding["ilink_bot_id"],
            ctx["from_user_id"],
            ctx["context_token"],
            text,
        )
    except Exception as e:
        print(f"[WeChat] {npc_name} 发送失败: {e}")


# ========== 查询 ==========

def is_wechat_conversation(npc_name: str) -> bool:
    """判断 NPC 当前是否在微信对话中"""
    with _state_lock:
        return npc_name in _wechat_contexts


def get_all_bindings() -> dict:
    """获取所有绑定状态 (供 API 使用)"""
    with _state_lock:
        result = {}
        for name, binding in _bindings.items():
            result[name] = {
                "status": "bound",
                "ilink_bot_id": binding["ilink_bot_id"],
            }
        return result


def cleanup_wechat_context(npc_name: str):
    """清理微信对话上下文 (对话结束时调用)"""
    with _state_lock:
        _wechat_contexts.pop(npc_name, None)
        _wechat_input_queue.pop(npc_name, None)  # 同时清理残留输入


def cleanup_all_wechat_state():
    """清理所有微信对话状态 (世界切换时调用)"""
    with _state_lock:
        _wechat_contexts.clear()
        _wechat_input_queue.clear()
        # _bindings 保留，因为绑定是持久化的


# ========== 启动恢复 ==========

def restore_bindings_from_npcs(npcs):
    """从 NPC 属性恢复绑定 (启动时调用)"""
    with _state_lock:
        for npc in npcs:
            if hasattr(npc, 'wechat_binding'):
                wb = npc.wechat_binding
                if wb and wb.get("status") == "bound":
                    _bindings[npc.name] = {
                        "bot_token": wb["bot_token"],
                        "ilink_bot_id": wb["ilink_bot_id"],
                        "wechat_uin": wb["wechat_uin"],
                        "get_updates_buf": "",
                    }
                    print(f"[WeChat] 恢复绑定: {npc.name}")
