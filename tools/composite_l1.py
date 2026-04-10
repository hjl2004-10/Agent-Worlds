# ============================================
# tools/composite_l1.py - 漫画排版拼图工具业务层
# 职责: 将多张图片按布局拼成漫画页面，叠加对话框和文字
# ============================================

import time
from pathlib import Path
from typing import List, Dict, Tuple


def _tool_composite_image(input_obj: dict, npc, context) -> str:
    """
    漫画排版拼图

    Args:
        input_obj: {
            "layout": "2x2",
            "panels": [{"image": "comic/images/p01.png", "dialogues": [...]}],
            "title": "可选标题",
            "output": "可选输出文件名"
        }
    """
    from PIL import Image, ImageDraw, ImageFont

    layout = input_obj.get("layout", "2x2").strip()
    panels = input_obj.get("panels", [])
    title = input_obj.get("title", "").strip()
    output_name = input_obj.get("output", "").strip()

    if not panels:
        return "错误: panels 列表为空"

    # 解析布局
    rows, cols = _parse_layout(layout, len(panels))

    # 解析工作目录
    from tools import tool as tool_module
    workdir = tool_module.WORKDIR or Path.cwd()

    # 加载图片
    images = []
    for i, panel in enumerate(panels):
        img_path = panel.get("image", "")
        if not img_path:
            return f"错误: 第 {i+1} 格缺少 image 路径"
        full_path = workdir / img_path
        if not full_path.exists():
            # 也试试项目根
            project_root = tool_module.PROJECT_ROOT or workdir.parent
            full_path = project_root / img_path
        if not full_path.exists():
            return f"错误: 找不到图片 {img_path}"
        try:
            images.append(Image.open(full_path).convert("RGBA"))
        except Exception as e:
            return f"错误: 加载图片 {img_path} 失败: {e}"

    # 配置参数
    PANEL_W = 512          # 每格宽
    PANEL_H = 512          # 每格高
    BORDER = 4             # 分格线宽度
    TITLE_H = 60 if title else 0
    BG_COLOR = (255, 255, 255, 255)
    BORDER_COLOR = (0, 0, 0, 255)

    canvas_w = cols * PANEL_W + (cols + 1) * BORDER
    canvas_h = rows * PANEL_H + (rows + 1) * BORDER + TITLE_H

    canvas = Image.new("RGBA", (canvas_w, canvas_h), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # 加载字体
    font_path = _find_font()
    title_font = ImageFont.truetype(font_path, 32) if font_path else ImageFont.load_default()
    dialogue_font = ImageFont.truetype(font_path, 20) if font_path else ImageFont.load_default()
    speaker_font = ImageFont.truetype(font_path, 16) if font_path else ImageFont.load_default()

    # 画标题
    if title:
        draw.rectangle([0, 0, canvas_w, TITLE_H], fill=BG_COLOR)
        bbox = draw.textbbox((0, 0), title, font=title_font)
        tw = bbox[2] - bbox[0]
        draw.text(((canvas_w - tw) // 2, 12), title, fill=(0, 0, 0), font=title_font)

    # 画分格线（先铺底色）
    draw.rectangle([0, TITLE_H, canvas_w, canvas_h], fill=BORDER_COLOR)

    # 逐格填充
    for idx in range(min(len(images), rows * cols)):
        r = idx // cols
        c = idx % cols
        x = BORDER + c * (PANEL_W + BORDER)
        y = TITLE_H + BORDER + r * (PANEL_H + BORDER)

        # 缩放图片填满格子
        img = images[idx]
        img_resized = img.resize((PANEL_W, PANEL_H), Image.LANCZOS)
        canvas.paste(img_resized, (x, y), img_resized)

        # 画对话框
        panel_data = panels[idx]
        dialogues = panel_data.get("dialogues", [])
        for dlg in dialogues:
            _draw_dialogue(draw, dlg, x, y, PANEL_W, PANEL_H, dialogue_font, speaker_font)

    # 输出
    if not output_name:
        timestamp = int(time.time())
        output_name = f"comic_{timestamp}.png"
    if not output_name.endswith(".png"):
        output_name += ".png"

    output_dir = workdir / "comic" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_name

    canvas_rgb = canvas.convert("RGB")
    canvas_rgb.save(output_path, "PNG")

    rel_path = f"comic/output/{output_name}"
    print(f"🖼️ [Composite] {npc.name}: {layout} 布局, {len(images)} 格 → {rel_path}")
    return f"漫画页已生成: {rel_path} ({rows}x{cols} 布局, {len(images)} 格)"


def _parse_layout(layout: str, panel_count: int) -> Tuple[int, int]:
    """解析布局字符串，返回 (rows, cols)"""
    layout = layout.lower().strip()

    # NxM 格式
    if "x" in layout:
        parts = layout.split("x")
        try:
            r, c = int(parts[0]), int(parts[1])
            if r > 0 and c > 0:
                return r, c
        except (ValueError, IndexError):
            pass

    # 根据数量自动布局
    if panel_count <= 1:
        return 1, 1
    elif panel_count <= 2:
        return 1, 2
    elif panel_count <= 4:
        return 2, 2
    elif panel_count <= 6:
        return 2, 3
    elif panel_count <= 9:
        return 3, 3
    else:
        cols = 4
        rows = (panel_count + cols - 1) // cols
        return rows, cols


def _draw_dialogue(draw, dlg: Dict, px: int, py: int,
                   pw: int, ph: int, text_font, speaker_font):
    """在指定格子区域内画对话框"""
    text = dlg.get("text", "").strip()
    if not text:
        return

    position = dlg.get("position", "top-left").lower()
    speaker = dlg.get("speaker", "").strip()

    # 对话框尺寸
    PADDING = 10
    MAX_W = pw * 2 // 3        # 最大占格子宽度的 2/3
    BUBBLE_RADIUS = 12

    # 自动换行
    lines = _wrap_text(draw, text, text_font, MAX_W - 2 * PADDING)

    # 计算气泡尺寸
    line_h = draw.textbbox((0, 0), "测", font=text_font)[3] + 4
    speaker_h = 0
    if speaker:
        speaker_h = draw.textbbox((0, 0), speaker, font=speaker_font)[3] + 6

    bubble_w = MAX_W
    bubble_h = speaker_h + len(lines) * line_h + 2 * PADDING

    # 位置计算
    margin = 12
    if "right" in position:
        bx = px + pw - bubble_w - margin
    else:
        bx = px + margin

    if "bottom" in position:
        by = py + ph - bubble_h - margin
    else:
        by = py + margin

    # 画气泡背景（圆角矩形）
    draw.rounded_rectangle(
        [bx, by, bx + bubble_w, by + bubble_h],
        radius=BUBBLE_RADIUS,
        fill=(255, 255, 255, 220),
        outline=(0, 0, 0, 180),
        width=2,
    )

    # 画说话人名字
    text_y = by + PADDING
    if speaker:
        draw.text((bx + PADDING, text_y), speaker, fill=(100, 100, 100), font=speaker_font)
        text_y += speaker_h

    # 画文字
    for line in lines:
        draw.text((bx + PADDING, text_y), line, fill=(0, 0, 0), font=text_font)
        text_y += line_h


def _wrap_text(draw, text: str, font, max_width: int) -> List[str]:
    """文字自动换行"""
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _find_font() -> str:
    """查找可用的中文字体（跨平台）"""
    import platform
    system = platform.system()

    candidates = []
    if system == "Windows":
        fonts_dir = Path("C:/Windows/Fonts")
        candidates = [
            fonts_dir / "msyh.ttc",      # 微软雅黑
            fonts_dir / "simhei.ttf",     # 黑体
            fonts_dir / "simsun.ttc",     # 宋体
        ]
    elif system == "Darwin":  # macOS
        candidates = [
            Path("/System/Library/Fonts/PingFang.ttc"),
            Path("/System/Library/Fonts/STHeiti Medium.ttc"),
            Path("/Library/Fonts/Arial Unicode.ttf"),
        ]
    else:  # Linux
        candidates = [
            Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
            Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
        ]

    for p in candidates:
        if p.exists():
            return str(p)
    return ""
