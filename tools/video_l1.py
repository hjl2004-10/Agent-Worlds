# ============================================
# tools/video_l1.py - 视频合成工具业务层
# 职责: 将图片序列 + 音频合成为视频 (moviepy)
# ============================================

import time
from pathlib import Path
from typing import List, Dict


def _tool_make_video(input_obj: dict, npc, context) -> str:
    """
    漫画视频合成 — 图片+配音合成为 MP4 视频

    Args:
        input_obj: {
            "panels": [
                {"image": "images/panel_01.png", "audio": "audio/voice_01.mp3", "duration": 4.0}
            ],
            "title": "漫画标题",
            "output": "comic_video.mp4"
        }
    """
    from moviepy import ImageClip, AudioFileClip, TextClip, concatenate_videoclips, CompositeVideoClip

    panels = input_obj.get("panels", [])
    title = input_obj.get("title", "").strip()
    output_name = input_obj.get("output", "").strip()
    fps = input_obj.get("fps", 24)

    if not panels:
        return "错误: panels 列表为空"

    # 解析工作目录
    from tools import tool as tool_module
    workdir = tool_module.WORKDIR or Path.cwd()
    project_root = tool_module.PROJECT_ROOT or workdir.parent

    # 自动生成文件名
    if not output_name:
        timestamp = int(time.time())
        output_name = f"comic_{timestamp}.mp4"
    if not output_name.endswith(".mp4"):
        output_name += ".mp4"

    output_dir = workdir / "comic" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_name

    print(f"🎬 [Video] {npc.name}: 合成 {len(panels)} 格视频...")

    clips = []

    # 标题卡片（如果有）
    if title:
        try:
            title_clip = _make_title_clip(title, duration=2.0)
            if title_clip:
                clips.append(title_clip)
        except Exception as e:
            print(f"🎬 [Video] 标题卡片生成失败 (跳过): {e}")

    # 逐格合成（支持视频片段或静态图片）
    for i, panel in enumerate(panels):
        video_path_str = panel.get("video", "")   # 视频片段（优先）
        img_path_str = panel.get("image", "")     # 静态图片（fallback）
        audio_path_str = panel.get("audio", "")
        duration = panel.get("duration", 4.0)

        # 智能检测: 如果 image 字段传入了 .mp4 文件，自动当视频处理
        if not video_path_str and img_path_str and img_path_str.endswith(".mp4"):
            video_path_str = img_path_str
            img_path_str = ""

        if not video_path_str and not img_path_str:
            return f"错误: 第 {i+1} 格缺少 video 或 image 路径"

        try:
            # 优先使用视频片段
            if video_path_str:
                from moviepy import VideoFileClip
                vp = _resolve_path(workdir, project_root, video_path_str)
                if vp and vp.exists():
                    clip = VideoFileClip(str(vp))
                    # 叠加配音音频（替换视频原声或静默视频）
                    if audio_path_str:
                        audio_path = _resolve_path(workdir, project_root, audio_path_str)
                        if audio_path and audio_path.exists():
                            audio_clip = AudioFileClip(str(audio_path))
                            clip = clip.with_audio(audio_clip)
                    clips.append(clip)
                    print(f"🎬 [Video] 第 {i+1} 格: {video_path_str} (视频 {clip.duration:.1f}s)")
                    continue
                else:
                    print(f"🎬 [Video] 第 {i+1} 格视频找不到: {video_path_str}，降级为图片")

            # Fallback: 静态图片
            img_path = _resolve_path(workdir, project_root, img_path_str)
            if not img_path or not img_path.exists():
                return f"错误: 找不到图片 {img_path_str}"

            img_clip = ImageClip(str(img_path))

            if audio_path_str:
                audio_path = _resolve_path(workdir, project_root, audio_path_str)
                if audio_path and audio_path.exists():
                    audio_clip = AudioFileClip(str(audio_path))
                    actual_duration = audio_clip.duration + 0.5
                    img_clip = img_clip.with_duration(actual_duration)
                    img_clip = img_clip.with_audio(audio_clip)
                else:
                    print(f"🎬 [Video] 第 {i+1} 格音频找不到: {audio_path_str}，使用静默")
                    img_clip = img_clip.with_duration(duration)
            else:
                img_clip = img_clip.with_duration(duration)

            clips.append(img_clip)
            print(f"🎬 [Video] 第 {i+1} 格: {img_path_str} (图片 {img_clip.duration:.1f}s)")

        except Exception as e:
            return f"错误: 第 {i+1} 格处理失败: {e}"

    if not clips:
        return "错误: 没有有效的视频片段"

    # 统一 clip 尺寸（以第一个 clip 为基准）
    base_w, base_h = clips[0].size
    for i in range(1, len(clips)):
        cw, ch = clips[i].size
        if cw != base_w or ch != base_h:
            print(f"🎬 [Video] 第 {i+1} 格尺寸 {cw}x{ch} → resize 到 {base_w}x{base_h}")
            clips[i] = clips[i].resized((base_w, base_h))

    # 拼接并输出
    try:
        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(
            str(output_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            logger=None,  # 静默输出
        )

        total_duration = final.duration or sum(c.duration for c in clips)
        rel_path = f"comic/output/{output_name}"

        # 清理
        final.close()
        for c in clips:
            c.close()

        print(f"🎬 [Video] 完成: {rel_path} ({total_duration:.1f}s)")
        return f"视频已生成: {rel_path} ({len(panels)} 格, {total_duration:.1f}秒)"

    except Exception as e:
        return f"错误: 视频合成失败: {e}"


def _resolve_path(workdir: Path, project_root: Path, path_str: str) -> Path:
    """解析相对路径"""
    p = workdir / path_str
    if p.exists():
        return p
    p = project_root / path_str
    if p.exists():
        return p
    return workdir / path_str  # 返回默认路径（可能不存在）


def _make_title_clip(title: str, duration: float = 2.0):
    """生成标题卡片（黑底白字）"""
    from moviepy import ColorClip, TextClip, CompositeVideoClip
    from tools.composite_l1 import _find_font

    font_path = _find_font()
    if not font_path:
        return None

    bg = ColorClip(size=(1280, 720), color=(15, 23, 42)).with_duration(duration)
    txt = TextClip(
        text=title,
        font=font_path,
        font_size=48,
        color="white",
    ).with_duration(duration).with_position("center")

    return CompositeVideoClip([bg, txt])
