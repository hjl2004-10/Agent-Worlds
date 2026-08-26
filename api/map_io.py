# api/map_io.py - 地图导入导出路由
# .hjlmap 包格式 (zip):
#   map.json                      # world.hjl + 全部场景四件套 合并的单文件描述
#   assets/tiles/*.png            # 瓦片素材
#   assets/house/*.png            # 建筑素材
#   assets/obstacles/*.gif        # 障碍物 GIF
#   assets/sprites/*.png          # (可选) 世界精灵池引用的精灵

import io
import json
import re
import struct
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/world", tags=["map-io"])

_PROJECT_ROOT = Path(__file__).parent.parent
WORLDS_DIR = _PROJECT_ROOT / 'data' / 'worlds'
PUBLIC_DIR = _PROJECT_ROOT / 'static' / 'public'

SCENE_FILES = ['scene.hjl', 'tiles.hjl', 'locations.hjl', 'obstacles.hjl']
ASSET_CATS = ['tiles', 'house', 'obstacles', 'sprites']

_SAFE_NAME = re.compile(r'^[a-zA-Z0-9_\-]{1,32}$')


def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _png_size(data: bytes):
    """解析 PNG IHDR 获取宽高; 非 PNG 返回 None"""
    if len(data) < 24 or data[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    w, h = struct.unpack('>II', data[16:24])
    return w, h


def _gif_size(data: bytes):
    """解析 GIF 逻辑屏幕尺寸; 非 GIF 返回 None"""
    if len(data) < 10 or data[:4] not in (b'GIF8',):
        return None
    w, h = struct.unpack('<HH', data[6:10])
    return w, h


# ========== 导出 ==========

def _collect_world_assets(world_data, scenes_data):
    """从场景数据收集素材引用 {类别: [文件名]}"""
    assets = {cat: set() for cat in ASSET_CATS}

    for scene in scenes_data.values():
        for row in scene.get('tiles', {}).get('tiles', []):
            for name in row:
                if name:
                    assets['tiles'].add(name)
        for loc in scene.get('locations', {}).get('locations', {}).values():
            b = loc.get('building')
            if b:
                assets['house'].add(Path(b.replace('\\', '/')).name)
        for obs in scene.get('obstacles', {}).get('obstacles', []):
            s = obs.get('sprite')
            if s:
                assets['obstacles'].add(Path(s.replace('\\', '/')).name)

    # 精灵池 (world.hjl assets.sprite_pool)
    for sid in (world_data.get('assets') or {}).get('sprite_pool', []):
        assets['sprites'].add(f"{sid}.png" if not sid.endswith('.png') else sid)

    return {cat: sorted(names) for cat, names in assets.items()}


@router.get("/export/{world_id}")
async def export_world(world_id: str):
    """导出世界为 .hjlmap 包 (zip 下载)"""
    world_dir = WORLDS_DIR / world_id
    world_data = _read_json(world_dir / 'world.hjl')
    if world_data is None:
        raise HTTPException(status_code=404, detail=f"世界不存在或缺少 world.hjl: {world_id}")

    scenes_data = {}
    scenes_root = world_dir / 'scenes'
    if scenes_root.exists():
        for sdir in sorted(scenes_root.iterdir()):
            if not sdir.is_dir():
                continue
            scene = {}
            for fname in SCENE_FILES:
                data = _read_json(sdir / fname)
                if data is not None:
                    scene[fname.replace('.hjl', '')] = data
            if 'scene' in scene:
                scenes_data[sdir.name] = scene

    if not scenes_data:
        raise HTTPException(status_code=400, detail=f"世界没有任何有效场景: {world_id}")

    manifest = _collect_world_assets(world_data, scenes_data)
    missing = {cat: [n for n in names if not (PUBLIC_DIR / cat / n).exists()]
               for cat, names in manifest.items()}
    missing = {cat: ns for cat, ns in missing.items() if ns}

    map_doc = {
        "format": "hjlmap",
        "version": "1.0",
        "world": world_data,
        "scenes": scenes_data,
        "assets": manifest,
        "export_info": {
            "missing_assets": missing,  # 引用了但本机不存在的素材 (导入端需自备)
        },
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('map.json', json.dumps(map_doc, ensure_ascii=False, indent=2))
        for cat, names in manifest.items():
            for name in names:
                fpath = PUBLIC_DIR / cat / name
                if fpath.exists():
                    zf.write(fpath, f'assets/{cat}/{name}')

    buf.seek(0)
    filename = f"{world_id}.hjlmap"
    return StreamingResponse(
        buf,
        media_type='application/octet-stream',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'X-Missing-Assets': json.dumps(missing, ensure_ascii=False)[:500],
        },
    )


# ========== 导入 ==========

def _validate_map_doc(doc):
    """校验 map.json 结构, 返回 (world_id, 警告列表)"""
    warns = []

    if not isinstance(doc, dict) or doc.get('format') != 'hjlmap':
        raise HTTPException(status_code=400, detail="不是有效的 .hjlmap 包 (缺少 format: hjlmap)")

    world = doc.get('world')
    if not isinstance(world, dict):
        raise HTTPException(status_code=400, detail="缺少 world 段")

    world_id = world.get('world_id')
    if not world_id or not _SAFE_NAME.match(str(world_id)):
        raise HTTPException(status_code=400, detail=f"非法 world_id: {world_id!r} (仅限字母/数字/_/-)")

    scenes = doc.get('scenes')
    if not isinstance(scenes, dict) or not scenes:
        raise HTTPException(status_code=400, detail="缺少 scenes 段或为空")

    for sid, scene in scenes.items():
        if not _SAFE_NAME.match(str(sid)):
            raise HTTPException(status_code=400, detail=f"非法场景名: {sid!r}")
        for key in ['scene', 'tiles', 'locations', 'obstacles']:
            if key not in scene:
                raise HTTPException(status_code=400, detail=f"场景 {sid} 缺少 {key}.hjl 数据")
        # 瓦片网格必须矩形且非空
        grid = scene['tiles'].get('tiles')
        if not isinstance(grid, list) or not grid or not isinstance(grid[0], list):
            raise HTTPException(status_code=400, detail=f"场景 {sid} 的瓦片网格无效")
        cols = len(grid[0])
        if cols == 0 or any(len(r) != cols for r in grid):
            raise HTTPException(status_code=400, detail=f"场景 {sid} 的瓦片网格不是矩形")

    return str(world_id), warns


def _validate_assets(zf: zipfile.ZipFile, doc, warns):
    """校验包内素材: 引用完整性(硬校验) + 尺寸规范(软警告)"""
    names_in_zip = set(zf.namelist())
    manifest = doc.get('assets') or {}

    # 1. 引用的瓦片/建筑/障碍物必须在包内 (精灵缺失仅警告, 可用宿主机已有素材)
    for cat in ['tiles', 'house', 'obstacles']:
        for name in manifest.get(cat, []):
            if f'assets/{cat}/{name}' not in names_in_zip:
                raise HTTPException(
                    status_code=400,
                    detail=f"包内缺少被引用的素材: assets/{cat}/{name}"
                )

    # 2. 尺寸规范校验 (警告)
    for entry in names_in_zip:
        if not entry.startswith('assets/') or entry.endswith('/'):
            continue
        parts = entry.split('/')
        if len(parts) != 3 or parts[1] not in ASSET_CATS:
            warns.append(f"忽略非标准路径: {entry}")
            continue
        cat, fname = parts[1], parts[2]
        if '/' in fname or '..' in fname or '\\' in fname:
            raise HTTPException(status_code=400, detail=f"非法素材文件名: {entry}")
        data = zf.read(entry)
        lower = fname.lower()
        if cat == 'tiles' and lower.endswith('.png'):
            size = _png_size(data)
            if size and size != (48, 48):
                warns.append(f"瓦片 {fname} 尺寸 {size[0]}x{size[1]} (规范 48x48)")
        elif cat == 'obstacles' and lower.endswith('.gif'):
            size = _gif_size(data)
            if size and size != (48, 48):
                warns.append(f"障碍物 {fname} 尺寸 {size[0]}x{size[1]} (规范 48x48)")
        elif cat == 'sprites' and lower.endswith('.png'):
            size = _png_size(data)
            if size and size != (1152, 288):
                warns.append(f"精灵 {fname} 尺寸 {size[0]}x{size[1]} (规范 1152x288)")

    return manifest


@router.post("/import")
async def import_world(
    file: UploadFile = File(...),
    overwrite: bool = Form(False),
):
    """导入 .hjlmap 包: 校验 -> 落盘世界数据 + 素材"""
    raw = await file.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="不是有效的 zip/.hjlmap 文件")

    if 'map.json' not in zf.namelist():
        raise HTTPException(status_code=400, detail="包内缺少 map.json")

    try:
        doc = json.loads(zf.read('map.json').decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=400, detail="map.json 解析失败")

    world_id, warns = _validate_map_doc(doc)
    manifest = _validate_assets(zf, doc, warns)

    world_dir = WORLDS_DIR / world_id
    if world_dir.exists() and not overwrite:
        raise HTTPException(
            status_code=409,
            detail=f"世界已存在: {world_id} (需 overwrite 确认覆盖)"
        )

    # ---- 落盘 ----
    world_dir.mkdir(parents=True, exist_ok=True)
    with open(world_dir / 'world.hjl', 'w', encoding='utf-8') as f:
        json.dump(doc['world'], f, ensure_ascii=False, indent=2)

    for sid, scene in doc['scenes'].items():
        sdir = world_dir / 'scenes' / sid
        sdir.mkdir(parents=True, exist_ok=True)
        for key in ['scene', 'tiles', 'locations', 'obstacles']:
            with open(sdir / f'{key}.hjl', 'w', encoding='utf-8') as f:
                json.dump(scene[key], f, ensure_ascii=False, indent=2)

    installed_assets = []
    for entry in zf.namelist():
        if not entry.startswith('assets/') or entry.endswith('/'):
            continue
        parts = entry.split('/')
        if len(parts) != 3 or parts[1] not in ASSET_CATS:
            continue
        cat, fname = parts[1], parts[2]
        if '/' in fname or '..' in fname or '\\' in fname:
            continue
        dest = PUBLIC_DIR / cat / fname
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(zf.read(entry))
        installed_assets.append(f'{cat}/{fname}')

    world_data = doc['world']
    return {
        "status": "ok",
        "world": {
            "world_id": world_id,
            "display_name": world_data.get('display_name', world_id),
            "genre": world_data.get('genre', '未知'),
            "description": world_data.get('description', ''),
            "available_scenes": world_data.get('available_scenes', []),
            "default_scene": world_data.get('default_scene', 'default'),
        },
        "installed_assets": len(installed_assets),
        "warnings": warns,
        "manifest_assets": {cat: len(v) for cat, v in manifest.items()},
    }
