# ============================================
# tools/asr_l1.py - ASR 语音识别工具业务层
# 职责: 调用百度短语音识别极速版，音频文件转文字
# ============================================

import json
import base64
import uuid
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


# 百度 ASR 配置 (从 config/services.json 读取)
_token_cache = None


def _tool_asr(input_obj: dict, npc, context) -> str:
    """
    语音识别 — 将音频文件转为文字

    Args:
        input_obj: {"file": "audio/recording.pcm", "format": "pcm"}
    """
    file_path = input_obj.get("file", "").strip()
    audio_format = input_obj.get("format", "pcm").strip()

    if not file_path:
        return "错误: 缺少 file 参数"

    # 解析文件路径
    from tools import tool as tool_module
    workdir = tool_module.WORKDIR or Path.cwd()
    full_path = workdir / file_path
    if not full_path.exists():
        project_root = tool_module.PROJECT_ROOT or workdir.parent
        full_path = project_root / file_path
    if not full_path.exists():
        return f"错误: 找不到音频文件 {file_path}"

    # 读取音频
    audio_data = full_path.read_bytes()
    if len(audio_data) > 10 * 1024 * 1024:  # 10MB 限制
        return "错误: 音频文件过大 (最大 10MB)"

    # 获取配置
    config = _get_asr_config()
    if not config:
        return "错误: 未配置 ASR 服务。请在 config/services.json 中添加 baidu_asr 配置"

    print(f"🎙️ [ASR] {npc.name}: 识别 {file_path} ({len(audio_data)} bytes)")

    try:
        # 获取 token
        token = _get_baidu_token(config)

        # 调用识别
        payload = json.dumps({
            "format": audio_format,
            "rate": 16000,
            "channel": 1,
            "cuid": f"kuafu-{uuid.uuid4().hex[:8]}",
            "dev_pid": 80001,
            "token": token,
            "speech": base64.b64encode(audio_data).decode(),
            "len": len(audio_data),
        }).encode()

        req = urllib.request.Request(
            "https://vop.baidu.com/pro_api",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())

        if result.get("err_no") != 0:
            return f"错误: 识别失败 [{result.get('err_no')}]: {result.get('err_msg')}"

        text = result["result"][0] if result.get("result") else ""
        print(f"🎙️ [ASR] 识别结果: {text[:50]}")
        return f"识别结果: {text}"

    except Exception as e:
        return f"错误: ASR 失败: {e}"


def _get_baidu_token(config: dict) -> str:
    """获取百度 access_token (缓存)"""
    global _token_cache
    if _token_cache:
        return _token_cache

    api_key = config.get("api_key", "")
    secret_key = config.get("secret_key", "")

    url = (
        f"https://aip.baidubce.com/oauth/2.0/token"
        f"?grant_type=client_credentials"
        f"&client_id={api_key}"
        f"&client_secret={secret_key}"
    )

    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())

    if "access_token" not in data:
        raise Exception(f"获取百度 token 失败: {data}")

    _token_cache = data["access_token"]
    print(f"🎙️ [ASR] 百度 token 获取成功")
    return _token_cache


def _get_asr_config() -> Optional[dict]:
    """从 config/services.json 获取百度 ASR 配置"""
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config" / "services.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get("baidu_asr")
    except Exception:
        return None
