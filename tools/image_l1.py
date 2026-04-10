# ============================================
# tools/image_l1.py - 图片生成/编辑工具业务层
# 职责: 调用云端图片 API，保存到 workspace
#
# 支持的渠道:
#   - image_zhipu (智谱 CogView)
#   - image_siliconflow (SiliconFlow Qwen-Image / Qwen-Image-Edit)
# ============================================

import json
import time
import base64
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Optional


def _tool_image_generate(input_obj: dict, npc, context) -> str:
    """
    生成图片

    Args:
        input_obj: {
            "prompt": "...",
            "size": "1024x1024",
            "channel": "image_siliconflow",  (可选，默认取第一个 image_ 渠道)
            "filename": "my_image.png"
        }
    """
    prompt = input_obj.get("prompt", "").strip()
    channel = input_obj.get("channel", "").strip()
    filename = input_obj.get("filename", "")

    if not prompt:
        return "错误: 缺少 prompt 参数"

    # 获取图片生成渠道配置
    config, channel_name = _get_image_config(channel)
    if not config:
        return "错误: 未配置图片生成渠道。请在 config/llm.json 中添加 image_* 渠道"

    # 尺寸: 参数优先，否则读配置默认值
    defaults = config.get("defaults", {})
    size = input_obj.get("size", defaults.get("size", "1024x1024"))

    # 自动生成文件名
    if not filename:
        timestamp = int(time.time())
        filename = f"gen_{timestamp}.png"

    # 只取文件名部分（NPC 可能传 "images/xxx.png"，去掉路径前缀）
    filename = Path(filename).name

    # 确保输出目录存在
    from tools import tool as tool_module
    workdir = tool_module.WORKDIR or Path.cwd()
    images_dir = workdir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / filename

    print(f"🎨 [ImageGen] {npc.name}: {prompt[:60]}... (channel={channel_name})")

    # 调用 API
    try:
        image_url = _call_image_api(config, {"prompt": prompt, "size": size})
    except Exception as e:
        return f"错误: 图片生成失败: {e}"

    if not image_url:
        return "错误: 图片生成 API 返回空数据"

    # 保存图片
    return _save_image(image_url, output_path, filename)


def _tool_image_edit(input_obj: dict, npc, context) -> str:
    """
    基于参考图编辑生成新图片（保持角色/风格一致性）

    支持单图或多图（最多3张），多图时横向拼接传给 Qwen-Image-Edit-2509。
    prompt 中用 "image 1", "image 2", "image 3" 引用不同参考图。

    Args:
        input_obj: {
            "prompt": "image 1 character doing ...",
            "image": "images/panel_01.png",         (单图，向后兼容)
            "images": ["images/a.png", "images/b.png"],  (多图，最多3张，优先)
            "size": "1024x1024",
            "channel": "image_siliconflow",
            "filename": "panel_02.png"
        }
    """
    prompt = input_obj.get("prompt", "").strip()
    single_image = input_obj.get("image", "").strip()
    multi_images = input_obj.get("images", [])
    size = input_obj.get("size", "1024x1024")
    channel = input_obj.get("channel", "").strip()
    filename = input_obj.get("filename", "")

    if not prompt:
        return "错误: 缺少 prompt 参数"

    # 确定参考图列表（images 优先，兼容单 image）
    image_paths = multi_images if multi_images else ([single_image] if single_image else [])
    if not image_paths:
        return "错误: 缺少 image 或 images 参数"
    if len(image_paths) > 3:
        return "错误: 最多支持 3 张参考图"

    # 解析所有参考图路径
    from tools import tool as tool_module
    workdir = tool_module.WORKDIR or Path.cwd()
    project_root = tool_module.PROJECT_ROOT or workdir.parent

    loaded_images = []
    for ip in image_paths:
        fp = workdir / ip
        if not fp.exists():
            fp = project_root / ip
        if not fp.exists():
            return f"错误: 找不到参考图 {ip}"
        loaded_images.append(fp)

    # 多图：横向拼接成一张大图（Qwen-Image-Edit-2509 支持）
    if len(loaded_images) > 1:
        from PIL import Image as PILImage
        pil_images = [PILImage.open(str(p)).convert("RGB") for p in loaded_images]
        # 统一高度为最小高度
        min_h = min(img.height for img in pil_images)
        resized = []
        for img in pil_images:
            if img.height != min_h:
                ratio = min_h / img.height
                img = img.resize((int(img.width * ratio), min_h), PILImage.LANCZOS)
            resized.append(img)
        total_w = sum(img.width for img in resized)
        merged = PILImage.new("RGB", (total_w, min_h))
        x_offset = 0
        for img in resized:
            merged.paste(img, (x_offset, 0))
            x_offset += img.width
        # 转 base64
        import io
        buf = io.BytesIO()
        merged.save(buf, format="PNG")
        image_b64 = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        ref_desc = f"{len(loaded_images)} 张参考图(拼接)"
    else:
        image_bytes = loaded_images[0].read_bytes()
        image_b64 = f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
        ref_desc = str(image_paths[0])

    # 获取渠道配置
    config, channel_name = _get_image_config(channel or "image_siliconflow")
    if not config:
        return "错误: 未配置支持图片编辑的渠道 (需要 image_siliconflow)"

    # 尺寸: 参数优先，否则读配置默认值
    defaults = config.get("defaults", {})
    size = input_obj.get("size", defaults.get("size", "1024x1024"))

    # 自动生成文件名
    if not filename:
        timestamp = int(time.time())
        filename = f"edit_{timestamp}.png"

    # 只取文件名部分
    filename = Path(filename).name

    images_dir = workdir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / filename

    print(f"🎨 [ImageEdit] {npc.name}: {prompt[:60]}... (ref={ref_desc})")

    # 调用 API
    try:
        image_url = _call_image_api(config, {
            "prompt": prompt,
            "size": size,
            "image": image_b64,
            "model": "Qwen/Qwen-Image-Edit-2509",
        })
    except Exception as e:
        return f"错误: 图片编辑失败: {e}"

    if not image_url:
        return "错误: 图片编辑 API 返回空数据"

    # 保存图片
    result = _save_image(image_url, output_path, filename)

    # 强制 resize 到标准尺寸（image_edit 输出尺寸可能受参考图拼接影响）
    try:
        target_w, target_h = map(int, size.split("x"))
        from PIL import Image as PILImage
        img = PILImage.open(str(output_path))
        if img.size != (target_w, target_h):
            img = img.resize((target_w, target_h), PILImage.LANCZOS)
            img.save(str(output_path))
            print(f"🎨 [ImageEdit] 已 resize 到 {target_w}x{target_h}")
    except Exception:
        pass  # resize 失败不影响主流程

    return result


# ========== 内部函数 ==========

def _get_image_config(channel: str = "") -> tuple:
    """获取图片渠道配置

    Args:
        channel: 指定渠道名（如 "image_siliconflow"），为空则取第一个 image_ 渠道

    Returns:
        (config_dict, channel_name) 或 (None, None)
    """
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config" / "llm.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        channels = config.get("channels", {})

        # 指定渠道
        if channel and channel in channels:
            return channels[channel], channel

        # 默认：找第一个 image_ 渠道
        for name, cfg in channels.items():
            if name.startswith("image"):
                return cfg, name
        return None, None
    except Exception:
        return None, None


def _call_image_api(config: Dict, params: Dict) -> Optional[str]:
    """统一的图片 API 调用，适配不同渠道的返回格式

    Args:
        config: 渠道配置
        params: {"prompt", "size", "image"(可选), "model"(可选)}

    Returns:
        图片 URL 或 base64 数据
    """
    base_url = config.get("base_url", "").rstrip("/")
    api_key = config.get("api_key", "")
    models = config.get("models", {})

    # 构建请求体
    body_dict = {
        "model": params.get("model", models.get("default", "")),
        "prompt": params["prompt"],
    }

    # size 字段：不同 API 用不同字段名
    size = params.get("size", "1024x1024")
    if "siliconflow" in base_url:
        body_dict["image_size"] = size
    else:
        body_dict["size"] = size

    # 图片编辑：传入原图
    if "image" in params:
        body_dict["image"] = params["image"]

    endpoint = config.get("endpoint", "/v1/images/generations")
    url = f"{base_url}{endpoint}"
    body = json.dumps(body_dict).encode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode())

    # 适配不同返回格式
    # SiliconFlow 格式: {"images": [{"url": "..."}]}
    images = result.get("images", [])
    if images:
        return images[0].get("url", "")

    # OpenAI/智谱 格式: {"data": [{"url": "..."} or {"b64_json": "..."}]}
    data = result.get("data", [])
    if data:
        item = data[0]
        return item.get("url", item.get("b64_json", ""))

    return None


def _save_image(image_data: str, output_path: Path, filename: str) -> str:
    """保存图片（URL 下载或 base64 解码）"""
    try:
        if image_data.startswith("http"):
            req = urllib.request.Request(image_data)
            with urllib.request.urlopen(req, timeout=30) as resp:
                output_path.write_bytes(resp.read())
        else:
            output_path.write_bytes(base64.b64decode(image_data))

        print(f"🎨 [Image] 保存: {output_path}")
        rel_path = f"images/{filename}"
        return f"图片已生成并保存到 {rel_path}"

    except Exception as e:
        return f"错误: 保存图片失败: {e}"
