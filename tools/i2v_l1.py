# ============================================
# tools/i2v_l1.py - 图转视频工具业务层
# 职责: 调用图生视频 API，图片转视频
#
# 支持渠道:
#   - volcano_video (火山引擎 豆包 Seedance)
#   - siliconflow (SiliconFlow Wan2.2-I2V)
# ============================================

import json
import time
import base64
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Optional

# 默认轮询配置 (可在 config/llm.json defaults 中覆盖)
DEFAULT_POLL_INTERVAL = 5
DEFAULT_MAX_POLL_TIME = 300


def _tool_image_to_video(input_obj: dict, npc, context) -> str:
    """
    图片转视频

    Args:
        input_obj: {
            "image": "images/panel_01.png",
            "prompt": "camera slowly pans, character walks",
            "filename": "clip_01.mp4"
        }
    """
    image_path = input_obj.get("image", "").strip()
    prompt = input_obj.get("prompt", "").strip()
    filename = input_obj.get("filename", "").strip()

    if not image_path:
        return "错误: 缺少 image 参数"
    if not prompt:
        return "错误: 缺少 prompt 参数（视频动作描述）"

    # 解析图片路径
    from tools import tool as tool_module
    workdir = tool_module.WORKDIR or Path.cwd()
    full_path = workdir / image_path
    if not full_path.exists():
        project_root = tool_module.PROJECT_ROOT or workdir.parent
        full_path = project_root / image_path
    if not full_path.exists():
        return f"错误: 找不到图片 {image_path}"

    # 获取渠道配置
    config = _get_i2v_config()
    if not config:
        return "错误: 未配置图转视频渠道。请在 config/llm.json 中添加 video_* 渠道"

    # 自动生成文件名
    if not filename:
        timestamp = int(time.time())
        filename = f"clip_{timestamp}.mp4"
    if not filename.endswith(".mp4"):
        filename += ".mp4"
    filename = Path(filename).name

    # 确保输出目录
    video_dir = workdir / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    output_path = video_dir / filename

    provider = config.get("provider", "")
    defaults = config.get("defaults", {})
    poll_interval = defaults.get("poll_interval", DEFAULT_POLL_INTERVAL)
    max_poll_time = defaults.get("max_poll_time", DEFAULT_MAX_POLL_TIME)

    print(f"🎬 [I2V] {npc.name}: {prompt[:50]}... (image={image_path}, provider={provider})")

    # 根据 provider 分发
    try:
        if provider == "volcano_video":
            video_url = _volcano_i2v(config, full_path, prompt, defaults, poll_interval, max_poll_time)
        else:
            video_url = _siliconflow_i2v(config, full_path, prompt, defaults, poll_interval, max_poll_time)
    except Exception as e:
        return f"错误: 视频生成失败: {e}"

    if not video_url:
        return "错误: 视频生成返回空结果"

    # 下载视频
    try:
        req = urllib.request.Request(video_url)
        with urllib.request.urlopen(req, timeout=60) as resp:
            output_path.write_bytes(resp.read())
        print(f"🎬 [I2V] 保存: {output_path}")
        return f"视频已生成: video/{filename}"
    except Exception as e:
        return f"错误: 下载视频失败: {e}"


# ========== 火山引擎 (豆包 Seedance) ==========

def _volcano_i2v(config: Dict, image_path: Path, prompt: str,
                 defaults: Dict, poll_interval: int, max_poll_time: int) -> str:
    """火山引擎图生视频 (豆包 Seedance) — 异步任务模式

    API 文档: https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks
    创建任务 → 轮询查询 → 拿视频 URL
    """
    base_url = config.get("base_url", "").rstrip("/")
    api_key = config.get("api_key", "")
    model = config.get("models", {}).get("default", "doubao-seedance-1-5-pro-251215")

    # 从 defaults 读取参数
    duration = defaults.get("duration", 5)
    watermark = defaults.get("watermark", False)
    camera_fixed = defaults.get("camerafixed", False)
    resolution = defaults.get("resolution", "720p")
    ratio = defaults.get("ratio", "16:9")
    generate_audio = defaults.get("generate_audio", False)

    # 根据 resolution + ratio 计算目标尺寸，确保图片符合 API 要求
    _RES_MAP = {
        ("720p", "16:9"): (1280, 720),
        ("720p", "9:16"): (720, 1280),
        ("720p", "1:1"): (720, 720),
        ("1080p", "16:9"): (1920, 1080),
        ("1080p", "9:16"): (1080, 1920),
        ("1080p", "1:1"): (1080, 1080),
    }
    target_size = _RES_MAP.get((resolution, ratio))

    # 验证并 resize 输入图片
    from PIL import Image as PILImage
    img = PILImage.open(str(image_path))
    if target_size and img.size != target_size:
        print(f"🎬 [I2V] 输入图片 {img.size} → resize 到 {target_size}")
        img = img.resize(target_size, PILImage.LANCZOS)
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()
        suffix = "png"
    else:
        image_bytes = image_path.read_bytes()
        suffix = image_path.suffix.lstrip(".") or "png"

    # 图片转 base64 data URL
    image_b64_url = f"data:image/{suffix};base64,{base64.b64encode(image_bytes).decode()}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # Step 1: 创建任务（新方式：参数在 body 顶层）
    submit_url = f"{base_url}/contents/generations/tasks"
    body_dict = {
        "model": model,
        "content": [
            {"type": "image_url", "image_url": {"url": image_b64_url}},
        ],
        "resolution": resolution,
        "ratio": ratio,
        "duration": duration,
        "camera_fixed": camera_fixed,
        "watermark": watermark,
        "generate_audio": generate_audio,
    }
    # 有提示词才加 text
    if prompt:
        body_dict["content"].insert(0, {"type": "text", "text": prompt})

    body = json.dumps(body_dict).encode()
    req = urllib.request.Request(submit_url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode())

    task_id = result.get("id", "")
    if not task_id:
        raise Exception(f"未返回 task id: {json.dumps(result, ensure_ascii=False)[:200]}")

    print(f"🎬 [I2V] 火山任务已提交: {task_id}")

    # Step 2: 轮询状态（GET 请求）
    query_url = f"{base_url}/contents/generations/tasks/{task_id}"
    elapsed = 0
    while elapsed < max_poll_time:
        time.sleep(poll_interval)
        elapsed += poll_interval

        req = urllib.request.Request(query_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
        except Exception as e:
            print(f"🎬 [I2V] 轮询异常 (继续): {e}")
            continue

        status = result.get("status", "")

        if status == "succeeded":
            content = result.get("content", {})

            # 格式1: content 是 dict，直接有 video_url 字段（火山引擎实际格式）
            if isinstance(content, dict):
                video_url = content.get("video_url", "")
                if isinstance(video_url, str) and video_url.startswith("http"):
                    return video_url

            # 格式2: content 是数组（文档描述的格式）
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "video_url":
                            vu = item.get("video_url", {})
                            url = vu.get("url", "") if isinstance(vu, dict) else str(vu)
                            if url.startswith("http"):
                                return url

            raise Exception(f"任务成功但未找到视频 URL。返回: {json.dumps(result, ensure_ascii=False)[:300]}")

        elif status in ("failed", "cancelled", "expired"):
            error_msg = result.get("error", {})
            if isinstance(error_msg, dict):
                error_msg = error_msg.get("message", str(error_msg))
            raise Exception(f"任务{status}: {error_msg}")

        elif elapsed % 30 == 0:
            print(f"🎬 [I2V] 等待中... ({elapsed}s, status={status})")

    raise Exception(f"视频生成超时 ({max_poll_time}秒)")


# ========== SiliconFlow (Wan2.2-I2V) ==========

def _siliconflow_i2v(config: Dict, image_path: Path, prompt: str,
                     defaults: Dict, poll_interval: int, max_poll_time: int) -> str:
    """SiliconFlow 图生视频 — 异步任务模式"""
    base_url = config.get("base_url", "").rstrip("/")
    api_key = config.get("api_key", "")
    model = config.get("models", {}).get("default", "Wan-AI/Wan2.2-I2V-A14B")
    image_size = defaults.get("image_size", "1280x720")

    image_bytes = image_path.read_bytes()
    image_b64 = f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # Step 1: 提交
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "image": image_b64,
        "image_size": image_size,
    }).encode()

    req = urllib.request.Request(f"{base_url}/v1/video/submit", data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode())

    request_id = result.get("requestId")
    if not request_id:
        raise Exception(f"未返回 requestId: {result}")

    print(f"🎬 [I2V] SiliconFlow 任务已提交: {request_id}")

    # Step 2: 轮询
    elapsed = 0
    while elapsed < max_poll_time:
        time.sleep(poll_interval)
        elapsed += poll_interval

        body = json.dumps({"requestId": request_id}).encode()
        req = urllib.request.Request(f"{base_url}/v1/video/status", data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
        except Exception as e:
            print(f"🎬 [I2V] 轮询异常 (继续): {e}")
            continue

        status = result.get("status", "")
        if status == "Succeed":
            videos = result.get("results", {}).get("videos", [])
            if videos and videos[0].get("url"):
                return videos[0]["url"]
        elif status == "Failed":
            raise Exception(f"视频生成失败: {result.get('reason', '未知')}")
        elif elapsed % 30 == 0:
            print(f"🎬 [I2V] 等待中... ({elapsed}s, status={status})")

    raise Exception(f"视频生成超时 ({max_poll_time}秒)")


# ========== 配置 ==========

def _get_i2v_config() -> Optional[Dict]:
    """从 config/llm.json 获取视频生成渠道配置"""
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config" / "llm.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        channels = config.get("channels", {})
        for name, cfg in channels.items():
            if name.startswith("video"):
                return cfg
        return None
    except Exception:
        return None
