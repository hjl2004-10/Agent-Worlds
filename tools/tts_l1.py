# ============================================
# tools/tts_l1.py - TTS 语音合成工具业务层
# 职责: 调用 SiliconFlow CosyVoice2 API，文本转语音保存 mp3
# ============================================

import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Optional


# 可用音色
VOICES = ["alex", "anna", "bella", "benjamin", "charles", "claire", "david", "diana"]


def _tool_tts(input_obj: dict, npc, context) -> str:
    """
    文本转语音

    Args:
        input_obj: {"text": "要合成的文本", "voice": "alex", "filename": "output.mp3"}
    """
    text = input_obj.get("text", "").strip()
    voice = input_obj.get("voice", "alex").strip()
    filename = input_obj.get("filename", "").strip()

    if not text:
        return "错误: 缺少 text 参数"

    if voice not in VOICES:
        return f"错误: 不支持的音色 '{voice}'。可用: {', '.join(VOICES)}"

    # 获取 TTS 渠道配置
    config = _get_tts_config()
    if not config:
        return "错误: 未配置 TTS 渠道。请在 config/llm.json 中添加 tts_* 渠道"

    # 自动生成文件名
    if not filename:
        timestamp = int(time.time())
        filename = f"tts_{timestamp}.mp3"
    if not filename.endswith(".mp3"):
        filename += ".mp3"

    # 确保输出目录存在
    from tools import tool as tool_module
    workdir = tool_module.WORKDIR or Path.cwd()
    audio_dir = workdir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_path = audio_dir / filename

    print(f"🔊 [TTS] {npc.name}: {text[:40]}... (voice={voice})")

    # 调用 API
    try:
        base_url = config.get("base_url", "").rstrip("/")
        api_key = config.get("api_key", "")
        model = config.get("models", {}).get("default", "FunAudioLLM/CosyVoice2-0.5B")
        defaults = config.get("defaults", {})

        # 从配置读取默认参数
        sample_rate = defaults.get("sample_rate", 32000)
        speed = defaults.get("speed", 1.0)
        response_format = defaults.get("response_format", "mp3")
        default_voice = defaults.get("voice", "alex")

        # voice: 参数优先，否则读配置默认值
        if not voice or voice == "alex":
            voice = voice or default_voice

        url = f"{base_url}/v1/audio/speech"
        body = json.dumps({
            "model": model,
            "input": text,
            "voice": f"{model}:{voice}",
            "response_format": response_format,
            "sample_rate": sample_rate,
            "speed": speed,
        }).encode()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                return f"错误: TTS API 返回 {resp.status}"
            output_path.write_bytes(resp.read())

        print(f"🔊 [TTS] 保存: {output_path}")
        rel_path = f"audio/{filename}"
        return f"语音已生成: {rel_path} (音色: {voice})"

    except Exception as e:
        return f"错误: TTS 失败: {e}"


def _get_tts_config() -> Optional[Dict]:
    """从 config/llm.json 获取 TTS 渠道配置"""
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config" / "llm.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        channels = config.get("channels", {})
        for name, cfg in channels.items():
            if name.startswith("tts"):
                return cfg
        return None
    except Exception:
        return None
