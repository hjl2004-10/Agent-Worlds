# ============================================
# core/debug/debug_log.py - LLM 调用调试日志 (总控)
# 职责: 内存环形队列存储最近 N 次 LLM 调用, 供 api/debug 查询
# ============================================

import threading
import time
from collections import deque

_MAX_LOGS = 200              # 环形队列容量
_RESPONSE_PREVIEW = 120     # 列表项里返回文本的预览长度

_logs = deque(maxlen=_MAX_LOGS)
_lock = threading.Lock()
_next_id = 1                 # 自增 id


def record_llm_call(speaker_name, listener_name, messages, response,
                    tool_calls, channel, model, conv_type='npc'):
    """记录一次 LLM 调用。

    messages: 发给 LLM 的完整请求 (list[{role,content}])
    response: 返回文本 (str)
    tool_calls: 工具调用列表 (list[dict]), 无则 []
    channel/model: 渠道与模型名
    conv_type: 对话类型 (npc/location/timer/wechat)
    返回: 该条记录的 id
    """
    global _next_id
    tool_calls = tool_calls or []
    with _lock:
        lid = _next_id
        _next_id += 1
        entry = {
            'id': lid,
            'ts': time.time(),
            'speaker': speaker_name,
            'listener': listener_name,
            'conv_type': conv_type,
            'channel': channel,
            'model': model,
            'message_count': len(messages or []),
            'messages': messages or [],          # 完整请求 (详情用)
            'response': response or '',           # 完整返回 (详情用)
            'tool_calls': tool_calls,             # 完整工具调用 (详情用)
        }
        _logs.append(entry)
    return lid


def _summary(entry):
    """列表项摘要 (不含完整 messages/response, 省带宽)。"""
    return {
        'id': entry['id'],
        'ts': entry['ts'],
        'speaker': entry['speaker'],
        'listener': entry['listener'],
        'conv_type': entry['conv_type'],
        'channel': entry['channel'],
        'model': entry['model'],
        'message_count': entry['message_count'],
        'tool_count': len(entry['tool_calls']),
        'response_preview': entry['response'][:_RESPONSE_PREVIEW],
    }


def get_logs(npc=None, limit=50):
    """返回最近 limit 条记录摘要 (最新在前)。npc 过滤 speaker 或 listener。"""
    with _lock:
        items = list(_logs)
    if npc:
        items = [x for x in items if x['speaker'] == npc or x['listener'] == npc]
    items = items[-limit:]
    items.reverse()
    return [_summary(x) for x in items]


def get_log(log_id):
    """返回单条完整记录 (含 messages/response/tool_calls), 没有返回 None。"""
    with _lock:
        for x in _logs:
            if x['id'] == log_id:
                return x
    return None
