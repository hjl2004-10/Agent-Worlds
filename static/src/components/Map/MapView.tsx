import { useEffect, useRef, useState } from 'react';
import { useNPCStore } from '@/store/useNPCStore';
import { useGodStore, godMoveDirectionRef, godPredictedPositionRef } from '@/store/useGodStore';

// 地图配置 (与后端同步)
// 16x16 图块制: 320x320 像素 = 20x20 图块
const TILE_SIZE = 16;
const MAP_WIDTH = 320;
const MAP_HEIGHT = 320;
const COLORS = ['#4ade80', '#38bdf8', '#e879f9', '#fbbf24', '#f87171'];

// ============ 环境氛围系统 ============

// Seeded PRNG (Mulberry32) — 按坐标确定性生成，不闪烁
function mulberry32(seed: number) {
  return () => {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// ============ 精灵图布局配置 ============
// 两种规格: 16x16 (帧 16x32) 和 48x48 (帧 48x96)

interface SpriteLayout {
  frameWidth: number;    // 单帧宽度
  frameHeight: number;   // 单帧高度 (是宽度的2倍)
  drawWidth: number;     // 渲染宽度
  drawHeight: number;    // 渲染高度
  assetId: string;       // 资源 ID
  walkRowY: number;      // 行走动画行的 Y 坐标
}

// 根据精灵 ID 解析布局配置
// 48x48 规格: 帧尺寸 48x96, 渲染时缩小到 16x24 (与 16x16 规格一致)
// 16x16 规格: 帧尺寸 16x32, 渲染尺寸 16x24
function resolveSpriteLayout(spriteId?: string): SpriteLayout {
  const rawId = spriteId || 'Adam';
  if (rawId.endsWith('_48x48')) {
    return {
      frameWidth: 48,
      frameHeight: 96,   // 48x96 帧
      drawWidth: 16,     // 缩小到 16x16 规格的渲染尺寸
      drawHeight: 24,    // 与 16x16 规格一致
      assetId: rawId,
      walkRowY: 96,      // 行走动画在第二行
    };
  }
  // 默认 16x16 规格
  return {
    frameWidth: 16,
    frameHeight: 32,     // 16x32 帧
    drawWidth: 16,
    drawHeight: 24,      // 渲染时稍微压缩
    assetId: rawId.endsWith('_16x16') ? rawId : rawId,
    walkRowY: 32,        // 行走动画在第二行
  };
}

// 方向到帧索引的映射 (适用于两种规格)
// 静止帧: right=0, up=1, left=2, down=3
// 行走帧: right=0-5, up=6-11, left=12-17, down=18-23
const IDLE_FRAME_MAP: Record<string, number> = {
  right: 0,
  up: 1,
  left: 2,
  down: 3,
};

const WALK_START_MAP: Record<string, number> = {
  right: 0,
  up: 6,
  left: 12,
  down: 18,
};

// 16x16 精灵图配置 (向后兼容，用于常量引用)

// 地点颜色
const LOCATION_COLORS: Record<string, string> = {
  '酒馆': '#fbbf24',
  '教堂': '#a78bfa',
  '图书馆': '#60a5fa',
  '广场': '#f472b6',
  '哨塔': '#34d399',
  '市场': '#fb923c',
  '井边': '#22d3ee',
  '铁匠铺': '#f87171',
  '码头': '#38bdf8',
};

// 视口配置
const VIEWPORT_SCALE = 1.5;
const SMOOTH_FACTOR = 0.08;

// 平滑移动配置
const POSITION_LERP_FACTOR = 0.15;  // 位置插值因子 (越大越快)
const GOD_MOVE_SPEED = 60;         // 上帝模式客户端预测速度 (像素/秒) — 与后端 env/map.py GOD_MOVE_SPEED 同步

// 缩放范围
// 最小缩放是动态的: 整张地图恰好撑满画布时的倍率 (由 getMinScale 计算)
const MAX_SCALE = 3.0;      // 最大缩放 (看更小范围)
const SCALE_STEP = 0.1;     // 每次滚轮缩放步长

// ============ 统一相机目标坐标函数 ============
// 所有需要计算相机目标的地方都调用此函数，确保一致性
interface RenderPositions {
  [name: string]: { x: number; y: number };
}

function getCameraTargetPosition(
  npcs: any[],
  selectedNPC: string | null,
  renderPositions: RenderPositions
): { x: number; y: number } {
  if (!selectedNPC) {
    return { x: MAP_WIDTH / 2, y: MAP_HEIGHT / 2 };
  }

  const targetNPC = npcs.find(n => n.name === selectedNPC);
  if (!targetNPC) {
    return { x: MAP_WIDTH / 2, y: MAP_HEIGHT / 2 };
  }

  // 上帝控制的 NPC 使用渲染位置 (客户端预测)
  if (targetNPC.god_controlled && renderPositions[selectedNPC]) {
    return renderPositions[selectedNPC];
  }

  // 其他情况使用后端位置
  return { x: targetNPC.x, y: targetNPC.y };
}

interface Location {
  name: string;
  x: number;
  y: number;
  building?: string;  // 建筑图片路径
  desc?: string;
}

function normalizePublicAssetPath(path?: string): string | null {
  if (!path) return null;
  const normalized = path
    .replace(/\\/g, '/')
    .replace(/^\/+/, '')
    .replace(/^public\//, '');
  return `/${normalized}`;
}

interface Obstacle {
  id: string;
  type: 'rect' | 'circle';
  x: number;
  y: number;
  width?: number;
  height?: number;
  radius?: number;
  desc?: string;
  sprite?: string;  // GIF 动画路径
}

interface MapViewProps {
  onNPCClick?: (name: string) => void;
}

export function MapView({ onNPCClick }: MapViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  // 动态最小缩放: 整张地图恰好完整撑满画布 (再小就会出现地图外的黑边)
  const getMinScale = () => {
    if (dimensions.width === 0 || dimensions.height === 0) return 0.5;
    const baseScale = Math.min(dimensions.width, dimensions.height) / (MAP_WIDTH / VIEWPORT_SCALE);
    const fitScale = Math.max(dimensions.width, dimensions.height) / MAP_WIDTH;
    return fitScale / baseScale;
  };
  const [locations, setLocations] = useState<Location[]>([]);
  const [obstacles, setObstacles] = useState<Obstacle[]>([]);
  const [sprites, setSprites] = useState<Record<string, HTMLImageElement>>({});
  const [tiles, setTiles] = useState<string[][]>([]);
  const [tileImages, setTileImages] = useState<Record<string, HTMLImageElement>>({});
  const [buildingImages, setBuildingImages] = useState<Record<string, HTMLImageElement>>({});
  const [statusIconOverlays, setStatusIconOverlays] = useState<{
    npcName: string;
    iconType: string;
    screenX: number;
    screenY: number;
    iconSize: number;  // 保存计算好的尺寸
  }[]>([]);
  const [obstacleOverlays, setObstacleOverlays] = useState<{
    id: string;
    sprite: string;
    screenX: number;
    screenY: number;
    size: number;
  }[]>([]);
  // 障碍物动画状态: 记录哪些障碍物当前在播放动画
  const [animatingObstacles, setAnimatingObstacles] = useState<Set<string>>(new Set());
  const obstacleAnimTimersRef = useRef<Record<string, { startTimer: ReturnType<typeof setTimeout>; stopTimer?: ReturnType<typeof setTimeout> }>>({});
  // 障碍物静态帧存储 (第一帧的 data URL)
  const obstacleStaticFramesRef = useRef<Record<string, string>>({});
  const npcsRef = useRef(useNPCStore.getState().npcs);
  const selectedNPCRef = useRef(useGodStore.getState().selectedNPC);

  // 客户端位置插值: 存储 NPC 的渲染位置 (平滑过渡)
  const renderPositionsRef = useRef<Record<string, { x: number; y: number }>>({});
  // 上帝控制的 NPC 的最后方向 (用于保留方向状态)
  const godLastDirectionRef = useRef<string | null>(null);
  // 注意: godMoveDirectionRef 从 useGodStore 导入

  // 状态图标时间戳追踪
  const npcStateTimestampsRef = useRef<Record<string, {
    walkModeStarted: number | null;  // 进入走路模式的时间
    idleStarted: number | null;      // 进入静止状态的时间
    lastWalkMode: string;            // 上一次的 walk_mode
  }>>({});

  // 缩放和拖动状态
  const [scale, setScale] = useState(1.0);
  const [isDragging, setIsDragging] = useState(false);
  const [isZooming, setIsZooming] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [manualOffset, setManualOffset] = useState({ x: 0, y: 0 });
  const [hasMoved, setHasMoved] = useState(false); // 是否发生了实际拖动
  const DRAG_THRESHOLD = 5; // 拖动阈值 (像素)
  const zoomTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 加载地点数据
  useEffect(() => {
    fetch('/api/locations')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'ok') {
          setLocations(data.locations);
          // 预加载建筑图片
          const buildingPaths = data.locations
            .filter((loc: Location) => loc.building)
            .map((loc: Location) => loc.building);
          const uniquePaths = [...new Set(buildingPaths as string[])];

          if (uniquePaths.length > 0) {
            const loadedBuildings: Record<string, HTMLImageElement> = {};
            let loadedCount = 0;

            uniquePaths.forEach((path: string) => {
              const img = new Image();
              const assetPath = normalizePublicAssetPath(path);
              if (!assetPath) {
                loadedCount++;
                return;
              }
              img.src = assetPath;
              img.onload = () => {
                loadedBuildings[path] = img;
                loadedCount++;
                if (loadedCount === uniquePaths.length) {
                  setBuildingImages(loadedBuildings);
                }
              };
              img.onerror = () => {
                console.warn(`Failed to load building: ${path}`);
                loadedCount++;
                if (loadedCount === uniquePaths.length) {
                  setBuildingImages(loadedBuildings);
                }
              };
            });
          }
        }
      })
      .catch(err => console.error('Failed to load locations:', err));
  }, []);

  // 加载障碍物数据
  useEffect(() => {
    fetch('/api/obstacles')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'ok') {
          setObstacles(data.obstacles);
        }
      })
      .catch(err => console.error('Failed to load obstacles:', err));
  }, []);

  // 障碍物随机动画控制: 5-10秒随机触发一次，播放2-3秒
  useEffect(() => {
    // 只对有 sprite 字段的障碍物启用动画
    const animatedObstacles = obstacles.filter(obs => obs.sprite);

    const startRandomAnimation = (obstacleId: string) => {
      // 随机等待 5-10 秒后开始动画
      const startDelay = 5000 + Math.random() * 5000;
      const startTimer = setTimeout(() => {
        // 开始播放动画
        setAnimatingObstacles(prev => new Set(prev).add(obstacleId));

        // 随机播放 2-3 秒后停止
        const playDuration = 2000 + Math.random() * 1000;
        const stopTimer = setTimeout(() => {
          setAnimatingObstacles(prev => {
            const next = new Set(prev);
            next.delete(obstacleId);
            return next;
          });
          // 递归触发下一次动画
          startRandomAnimation(obstacleId);
        }, playDuration);

        // 保存停止定时器
        if (obstacleAnimTimersRef.current[obstacleId]) {
          obstacleAnimTimersRef.current[obstacleId].stopTimer = stopTimer;
        }
      }, startDelay);

      // 保存开始定时器
      obstacleAnimTimersRef.current[obstacleId] = { startTimer };
    };

    // 为每个障碍物启动随机动画循环 (错开初始时间)
    animatedObstacles.forEach((obs, index) => {
      // 错开初始启动时间，避免同时触发
      setTimeout(() => startRandomAnimation(obs.id), index * 1000);
    });

    // 清理函数
    return () => {
      Object.values(obstacleAnimTimersRef.current).forEach(timers => {
        clearTimeout(timers.startTimer);
        if (timers.stopTimer) clearTimeout(timers.stopTimer);
      });
      obstacleAnimTimersRef.current = {};
    };
  }, [obstacles]);

  // 加载瓦片数据
  useEffect(() => {
    fetch('/api/tiles')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'ok' && data.tiles && data.tiles.length > 0) {
          setTiles(data.tiles);
          // 预加载所有用到的瓦片图片
          const uniqueTileNames = new Set<string>();
          data.tiles.forEach((row: string[]) => {
            row.forEach((name: string) => uniqueTileNames.add(name));
          });

          const loadedImages: Record<string, HTMLImageElement> = {};
          let loadedCount = 0;
          const total = uniqueTileNames.size;

          uniqueTileNames.forEach(name => {
            const img = new Image();
            img.src = `/tiles/${name}`;
            img.onload = () => {
              loadedImages[name] = img;
              loadedCount++;
              if (loadedCount === total) {
                setTileImages(loadedImages);
              }
            };
            img.onerror = () => {
              loadedCount++;
              if (loadedCount === total) {
                setTileImages(loadedImages);
              }
            };
          });
        }
      })
      .catch(err => console.error('Failed to load tiles:', err));
  }, []);

  // 加载精灵图 (动态从 API 获取列表)
  useEffect(() => {
    // 先尝试从 API 获取精灵列表，失败则使用默认列表
    const defaultSpriteIds = ['Adam', 'Alex', 'Amelia', 'Ash', 'Bob', 'Bruce', 'Dan', 'Edward', 'Lucy', 'Molly'];

    const loadSprites = (spriteIds: string[]) => {
      const loadedSprites: Record<string, HTMLImageElement> = {};
      let loadedCount = 0;

      spriteIds.forEach(id => {
        const img = new Image();
        // 根据 ID 后缀决定文件名格式
        const fileName = id.endsWith('_48x48') ? id : `${id}_16x16`;
        img.src = `/sprites/${fileName}.png`;
        img.onload = () => {
          loadedSprites[id] = img;
          loadedCount++;
          if (loadedCount === spriteIds.length) {
            setSprites(loadedSprites);
          }
        };
        img.onerror = () => {
          console.warn(`Failed to load sprite: ${id}`);
          loadedCount++;
          if (loadedCount === spriteIds.length) {
            setSprites(loadedSprites);
          }
        };
      });
    };

    fetch('/api/sprites')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'ok' && Array.isArray(data.sprites) && data.sprites.length > 0) {
          loadSprites(data.sprites);
        } else {
          loadSprites(defaultSpriteIds);
        }
      })
      .catch(() => {
        loadSprites(defaultSpriteIds);
      });
  }, []);

  // 订阅 store 更新
  useEffect(() => {
    const unsubscribeNPC = useNPCStore.subscribe((state) => {
      npcsRef.current = state.npcs;
    });
    const unsubscribeGod = useGodStore.subscribe((state) => {
      // 取消上帝控制时，清除保存的方向
      if (selectedNPCRef.current && !state.selectedNPC) {
        godLastDirectionRef.current = null;
      }
      selectedNPCRef.current = state.selectedNPC;
    });
    return () => {
      unsubscribeNPC();
      unsubscribeGod();
    };
  }, []);

  // 视口中心 (平滑跟随)
  const viewportRef = useRef({ x: MAP_WIDTH / 2, y: MAP_HEIGHT / 2 });
  const scaleRef = useRef(1.0);
  const manualOffsetRef = useRef({ x: 0, y: 0 });

  // 同步 ref
  useEffect(() => {
    scaleRef.current = scale;
  }, [scale]);

  // 整张地图预渲染到离屏画布 (一次成型，每帧只画一张大图，消除瓦片接缝闪烁)
  const mapCanvasRef = useRef<HTMLCanvasElement | null>(null);
  useEffect(() => {
    if (tiles.length === 0 || Object.keys(tileImages).length === 0) {
      mapCanvasRef.current = null;
      return;
    }
    const off = document.createElement('canvas');
    off.width = MAP_WIDTH;
    off.height = MAP_HEIGHT;
    const octx = off.getContext('2d');
    if (!octx) {
      mapCanvasRef.current = null;
      return;
    }
    octx.imageSmoothingEnabled = false;
    for (let ty = 0; ty < tiles.length; ty++) {
      for (let tx = 0; tx < tiles[ty].length; tx++) {
        const img = tileImages[tiles[ty][tx]];
        if (!img) continue;
        // 源 48x48 -> 目标 16x16，先取整到整数格避免累积误差
        octx.drawImage(img, 0, 0, 48, 48, tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE);
      }
    }
    mapCanvasRef.current = off;
  }, [tiles, tileImages]);

  // 按 renderScale 预放大缓存的地图 (缩放变化时才重建；滚动时 1:1 整数偏移，零重采样)
  const scaledMapRef = useRef<{ key: string; canvas: HTMLCanvasElement } | null>(null);
  // 小地图独立画布 (DOM 层级在 GIF 覆盖层之上，不被贴图遮挡)
  const miniMapCanvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    manualOffsetRef.current = manualOffset;
  }, [manualOffset]);

  // 清理缩放 timeout
  useEffect(() => {
    return () => {
      if (zoomTimeoutRef.current) {
        clearTimeout(zoomTimeoutRef.current);
      }
    };
  }, []);

  // 响应式尺寸
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        setDimensions({ width: clientWidth, height: clientHeight });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // 游戏循环 - 持续动画更新
  useEffect(() => {
    if (dimensions.width === 0) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 关键: 禁用图像平滑，保持像素清晰
    ctx.imageSmoothingEnabled = false;

    let animationId: number;
    let lastTime = 0;
    let frameTimer = 0;
    const frameInterval = 0.11; // 帧间隔 (秒)，与参考实现一致

    const render = (timestamp: number) => {
      const delta = Math.min((timestamp - lastTime) / 1000 || 0, 0.033);
      lastTime = timestamp;

      // 关键: 禁用图像平滑 (每帧设置，防止 canvas 尺寸变化后状态被重置)
      ctx.imageSmoothingEnabled = false;

      // 更新帧计时器 (用于行走动画)
      frameTimer += delta;

      const npcs = npcsRef.current;
      const selectedNPC = selectedNPCRef.current;
      const { width, height } = dimensions;
      const viewport = viewportRef.current;

      // ============ 客户端位置插值 + 上帝模式预测 ============
      const renderPositions = renderPositionsRef.current;
      const godDirection = godMoveDirectionRef.current;

      npcs.forEach(npc => {
        if (!renderPositions[npc.name]) {
          renderPositions[npc.name] = { x: npc.x, y: npc.y };
        }

        const rp = renderPositions[npc.name];
        const isSelectedGodNPC = npc.name === selectedNPC && (npc as any).god_controlled;

        if (isSelectedGodNPC) {
          // ====== 客户端预测: 按键时立即移动，不等后端 ======
          if (godDirection) {
            const speed = GOD_MOVE_SPEED * delta;
            switch (godDirection) {
              case 'up':    rp.y -= speed; break;
              case 'down':  rp.y += speed; break;
              case 'left':  rp.x -= speed; break;
              case 'right': rp.x += speed; break;
            }
            // 边界钳制
            rp.x = Math.max(2, Math.min(MAP_WIDTH - 2, rp.x));
            rp.y = Math.max(2, Math.min(MAP_HEIGHT - 2, rp.y));
          }

          // 后端坐标校正策略 (前后端速度统一为 60px/s，松键时前端会提交最终位置):
          // - 按键中: 轻微校正 (0.02)，前端预测主导，后端按同速推进
          // - 松键后: stop 已把最终位置提交给后端，误差≈0，用较强校正快速收敛
          const drift = Math.abs(npc.x - rp.x) + Math.abs(npc.y - rp.y);
          const correctionStrength = godDirection
            ? (drift > 30 ? 0.06 : 0.02)   // 漂移太大时稍微拉一下
            : 0.25;
          rp.x += (npc.x - rp.x) * correctionStrength;
          rp.y += (npc.y - rp.y) * correctionStrength;
        } else {
          // 其他 NPC: 平滑插值跟随后端坐标
          rp.x += (npc.x - rp.x) * POSITION_LERP_FACTOR;
          rp.y += (npc.y - rp.y) * POSITION_LERP_FACTOR;
        }
      });

      // 同步上帝控制 NPC 的预测位置到全局 ref (用于退出控制时提交)
      if (selectedNPC && renderPositions[selectedNPC]) {
        const controlledNpc = npcs.find(n => n.name === selectedNPC);
        if (controlledNpc && (controlledNpc as any).god_controlled) {
          godPredictedPositionRef.current = {
            x: renderPositions[selectedNPC].x,
            y: renderPositions[selectedNPC].y,
          };
        }
      }

      // 计算目标位置 (使用统一函数)
      const { x: targetX, y: targetY } = getCameraTargetPosition(npcs, selectedNPC, renderPositions);

      // 平滑跟随 (仅在没有手动操作时)
      if (!isDragging && !isZooming) {
        const finalTargetX = targetX + manualOffsetRef.current.x;
        const finalTargetY = targetY + manualOffsetRef.current.y;
        // 上帝模式下镜头更紧跟，普通模式下更丝滑
        const isGodActive = selectedNPC && npcs.find(n => n.name === selectedNPC && (n as any).god_controlled);
        const camSmooth = isGodActive && godDirection ? 0.18 : SMOOTH_FACTOR;
        viewport.x += (finalTargetX - viewport.x) * camSmooth;
        viewport.y += (finalTargetY - viewport.y) * camSmooth;
      }

      // 应用缩放 (下限为动态的"整图撑满画布"，防止缩小到地图外)
      const currentScale = Math.max(getMinScale(), Math.min(MAX_SCALE, scaleRef.current));

      // 计算视口范围 - 填满整个长方形画布
      // 基准视口大小 (在 1x 缩放下的可视地图范围)
      const baseViewSize = MAP_WIDTH / VIEWPORT_SCALE;

      // 分别计算 X 和 Y 方向的可视范围，填满画布
      // renderScale 表示每个地图像素对应多少画布像素
      const renderScale = Math.min(width, height) / baseViewSize * currentScale;

      // 视口在地图上的实际宽高 (保持 1:1 像素比例)
      const viewWidth = width / renderScale;
      const viewHeight = height / renderScale;

      // 视口中心钳制: 视口比地图小时限制在边界内; 视口大于等于地图时让地图居中
      // (不再钉死在左上角露出黑边)
      if (viewWidth >= MAP_WIDTH) viewport.x = MAP_WIDTH / 2;
      else viewport.x = Math.max(viewWidth / 2, Math.min(MAP_WIDTH - viewWidth / 2, viewport.x));
      if (viewHeight >= MAP_HEIGHT) viewport.y = MAP_HEIGHT / 2;
      else viewport.y = Math.max(viewHeight / 2, Math.min(MAP_HEIGHT - viewHeight / 2, viewport.y));

      // 视口边界 (不做 0/MAP 钳制，地图小于视口时自然居中)
      const minX = viewport.x - viewWidth / 2;
      const maxX = viewport.x + viewWidth / 2;
      const minY = viewport.y - viewHeight / 2;
      const maxY = viewport.y + viewHeight / 2;

      const actualViewWidth = maxX - minX;
      const actualViewHeight = maxY - minY;

      // 像素对齐: 相机量化到整地图像素 (所有图层共用同一基准，杜绝亚像素采样抖动)
      const camMinX = Math.round(minX);
      const camMinY = Math.round(minY);

      // 坐标转换函数: 地图坐标 -> 画布坐标 (基于量化后的相机)
      const mapToCanvas = (mapX: number, mapY: number) => ({
        x: (mapX - camMinX) * renderScale,
        y: (mapY - camMinY) * renderScale,
      });

      // 清空画布 (深色带微妙蓝调)
      ctx.fillStyle = '#0a0a16';
      ctx.fillRect(0, 0, width, height);

      // 绘制瓦片地图: 预放大缓存 + 1:1 整数偏移绘制 (滚动时零重采样，彻底消除闪烁)
      const mapCanvas = mapCanvasRef.current;
      if (mapCanvas) {
        const scaleKey = String(Math.round(renderScale * 1000));
        let scaled = scaledMapRef.current;
        if (!scaled || scaled.key !== scaleKey) {
          const w = Math.ceil(MAP_WIDTH * renderScale) + 2;
          const h = Math.ceil(MAP_HEIGHT * renderScale) + 2;
          const c = document.createElement('canvas');
          c.width = w;
          c.height = h;
          const cctx = c.getContext('2d');
          if (cctx) {
            cctx.imageSmoothingEnabled = false;
            cctx.drawImage(mapCanvas, 0, 0, w, h);
          }
          scaled = { key: scaleKey, canvas: c };
          scaledMapRef.current = scaled;
        }
        const dx = Math.round(-camMinX * renderScale);
        const dy = Math.round(-camMinY * renderScale);
        ctx.drawImage(scaled.canvas, dx, dy);
      } else {
        // 降级: 绘制深色地面纹理 (代替网格线)
        // 基础地面色
        ctx.fillStyle = '#181820';
        ctx.fillRect(0, 0, width, height);

        // 微妙的地面纹理噪点
        const tRng = mulberry32(7777);
        ctx.globalAlpha = 0.08;
        for (let i = 0; i < 200; i++) {
          const nx = tRng() * width;
          const ny = tRng() * height;
          const ns = 1 + tRng() * 3;
          ctx.fillStyle = tRng() > 0.5 ? '#444' : '#222';
          ctx.fillRect(nx, ny, ns, ns);
        }
        ctx.globalAlpha = 1;
      } // end else (降级地面)

      // 收集障碍物 GIF 覆盖层数据
      const obsOverlays: { id: string; sprite: string; screenX: number; screenY: number; size: number }[] = [];

      // 绘制障碍物 (有 sprite 字段的用 GIF 覆盖层，无 sprite 的用 Canvas 绘制)
      obstacles.forEach(obs => {
        // 检查是否在视口内
        const obsWidth = obs.type === 'rect' ? (obs.width || 48) : (obs.radius || 12) * 2;
        const obsHeight = obs.type === 'rect' ? (obs.height || 48) : (obs.radius || 12) * 2;
        if (obs.x + obsWidth < minX - 5 || obs.x > maxX + 5 || obs.y + obsHeight < minY - 5 || obs.y > maxY + 5) {
          return;
        }

        if (obs.sprite) {
          // 有 sprite 字段: 收集到 GIF 覆盖层 (坐标取整，避免 CSS 亚像素抖动)
          const { x: screenX, y: screenY } = mapToCanvas(obs.x, obs.y);
          const size = 48 * renderScale;  // 48x48 素材
          obsOverlays.push({
            id: obs.id,
            sprite: obs.sprite,
            screenX: Math.round(screenX),
            screenY: Math.round(screenY),
            size: size,
          });
        } else if (obs.type === 'rect') {
          // 矩形障碍物 (墙壁/建筑) — 坐标取整
          const topLeft = mapToCanvas(obs.x, obs.y);
          const bottomRight = mapToCanvas(obs.x + (obs.width || 0), obs.y + (obs.height || 0));
          const rx = Math.round(topLeft.x);
          const ry = Math.round(topLeft.y);
          const rectWidth = Math.round(bottomRight.x) - rx;
          const rectHeight = Math.round(bottomRight.y) - ry;

          // 障碍物填充 (深色)
          ctx.fillStyle = '#1a1410';
          ctx.fillRect(rx, ry, rectWidth, rectHeight);

          // 障碍物边框 (深棕色)
          ctx.strokeStyle = '#3d2817';
          ctx.lineWidth = 2;
          ctx.strokeRect(rx, ry, rectWidth, rectHeight);

          // 内部纹理 (更深的阴影)
          ctx.fillStyle = '#0f0a07';
          const innerPadding = 3;
          ctx.fillRect(
            rx + innerPadding,
            ry + innerPadding,
            rectWidth - innerPadding * 2,
            rectHeight - innerPadding * 2
          );
        } else if (obs.type === 'circle') {
          // 圆形障碍物 (树木/石头) — 坐标取整
          const { x: fx, y: fy } = mapToCanvas(obs.x, obs.y);
          const x = Math.round(fx);
          const y = Math.round(fy);
          const radius = (obs.radius || 5) * renderScale;

          // 树木/石头阴影
          ctx.beginPath();
          ctx.arc(x + 2, y + 2, radius, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
          ctx.fill();

          // 主体 (深色)
          ctx.beginPath();
          ctx.arc(x, y, radius, 0, Math.PI * 2);
          ctx.fillStyle = obs.desc?.includes('树') ? '#0d2d0d' : '#2a2a2a';
          ctx.fill();

          // 高光 (稍微亮一点)
          ctx.beginPath();
          ctx.arc(x - radius * 0.3, y - radius * 0.3, radius * 0.4, 0, Math.PI * 2);
          ctx.fillStyle = obs.desc?.includes('树') ? '#1a4a1a' : '#4a4a4a';
          ctx.fill();
        }
      });

      // 更新障碍物 GIF 覆盖层
      setObstacleOverlays(obsOverlays);

      // ============ Y-sorted 场景渲染 (建筑 + 地点) ============
      // 先按 Y 坐标排序，实现正确的遮挡关系
      const sortedLocations = [...locations].sort((a, b) => a.y - b.y);

      sortedLocations.forEach(loc => {
        if (loc.x < minX - 30 || loc.x > maxX + 30 || loc.y < minY - 30 || loc.y > maxY + 30) {
          return;
        }

        // 坐标取整 (缩放 drawImage 的小数目标坐标会导致采样相位每帧漂移 = 建筑抖动)
        const { x: fx, y: fy } = mapToCanvas(loc.x, loc.y);
        const x = Math.round(fx);
        const y = Math.round(fy);
        const color = LOCATION_COLORS[loc.name] || '#e879f9';

        // 建筑尺寸: 32 地图像素 (2x2 图块)，随缩放同步变化
        const buildingSize = 32 * renderScale;
        const halfSize = buildingSize / 2;
        // 地点名牌字号: 随缩放变化 (默认缩放下约 10px 不变)，限制 8~24px 保证可读
        const fontPx = Math.round(Math.max(8, Math.min(24, 3 * renderScale)));

        if (loc.building && buildingImages[loc.building]) {
          // === 建筑阴影 ===
          ctx.save();
          ctx.fillStyle = 'rgba(0, 0, 0, 0.25)';
          ctx.beginPath();
          ctx.ellipse(x + 3, y + halfSize + 2, halfSize * 0.9, halfSize * 0.3, 0, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();

          // === 建筑地面光晕 (温暖的灯光) ===
          const glowGradient = ctx.createRadialGradient(x, y, 2, x, y + 5, halfSize * 1.8);
          glowGradient.addColorStop(0, color + '18');
          glowGradient.addColorStop(0.5, color + '08');
          glowGradient.addColorStop(1, 'transparent');
          ctx.fillStyle = glowGradient;
          ctx.beginPath();
          ctx.arc(x, y + 5, halfSize * 1.8, 0, Math.PI * 2);
          ctx.fill();

          // === 渲染建筑图片 (目标坐标/尺寸取整，避免采样抖动) ===
          const halfR = Math.round(halfSize);
          ctx.drawImage(
            buildingImages[loc.building],
            x - halfR,
            y - halfR,
            halfR * 2,
            halfR * 2
          );

          // === 地点名称 (像素风名牌，随缩放同步) ===
          ctx.font = `bold ${fontPx}px "Press Start 2P", monospace`;
          ctx.textAlign = 'center';
          const nameWidth = ctx.measureText(loc.name).width;

          // 名牌背景 (锚定在建筑底部下方，间距随缩放)
          const nameY = y + halfR + Math.round(4 * renderScale);
          const pad = Math.max(2, Math.round(1.2 * renderScale));
          const boxTop = nameY - Math.round(fontPx * 0.9);
          const boxH = Math.round(fontPx * 1.3);
          const boxX = Math.round(x - nameWidth / 2 - pad);
          const boxW = Math.round(nameWidth + pad * 2);
          ctx.fillStyle = 'rgba(0, 0, 0, 0.65)';
          ctx.fillRect(boxX, boxTop, boxW, boxH);
          // 名牌边框
          ctx.strokeStyle = color + '80';
          ctx.lineWidth = 1;
          ctx.strokeRect(boxX, boxTop, boxW, boxH);
          // 名字文字
          ctx.fillStyle = color;
          ctx.fillText(loc.name, x, nameY);
        } else {
          // 无建筑时使用原来的菱形标记 + 增强光晕 (尺寸随缩放)
          const glowR = Math.round(9 * renderScale);
          const gradient = ctx.createRadialGradient(x, y, 0, x, y, glowR);
          gradient.addColorStop(0, color + '50');
          gradient.addColorStop(0.4, color + '20');
          gradient.addColorStop(1, 'transparent');
          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.arc(x, y, glowR, 0, Math.PI * 2);
          ctx.fill();

          // 地点标记 (菱形 + 脉动动画)
          const diaR = Math.round(2.3 * renderScale);
          const pulse = 0.9 + Math.sin(Date.now() / 800) * 0.1;
          ctx.save();
          ctx.translate(x, y);
          ctx.rotate(Math.PI / 4);
          ctx.scale(pulse, pulse);
          ctx.fillStyle = color;
          ctx.fillRect(-diaR, -diaR, diaR * 2, diaR * 2);
          ctx.strokeStyle = '#fff';
          ctx.lineWidth = 1.5;
          ctx.strokeRect(-diaR, -diaR, diaR * 2, diaR * 2);
          ctx.restore();

          // 地点名称
          ctx.font = `bold ${fontPx}px "Press Start 2P", monospace`;
          ctx.textAlign = 'center';
          ctx.fillStyle = color;
          ctx.strokeStyle = '#000';
          ctx.lineWidth = Math.round(fontPx * 0.3);
          const nameOff = Math.round(8 * renderScale);
          ctx.strokeText(loc.name, x, y + nameOff);
          ctx.fillText(loc.name, x, y + nameOff);
        }
      });

      // 绘制 NPC
      const iconOverlays: { npcName: string; iconType: string; screenX: number; screenY: number; iconSize: number }[] = [];
      npcs.forEach((npc, index) => {
        // 使用插值后的渲染位置
        const rp = renderPositions[npc.name] || { x: npc.x, y: npc.y };
        if (rp.x < minX - 5 || rp.x > maxX + 5 || rp.y < minY - 5 || rp.y > maxY + 5) {
          return;
        }

        // 坐标取整 (阴影/光环/名牌/图标全部基于整数坐标，避免亚像素抖动)
        const { x: fx, y: fy } = mapToCanvas(rp.x, rp.y);
        const x = Math.round(fx);
        const y = Math.round(fy);
        const color = COLORS[index % COLORS.length];
        const isSelected = npc.name === selectedNPC;
        const isTalking = npc.is_talking;
        const isPlayer = npc.is_player;
        const isEnabled = (npc as any).enabled !== false;  // 默认启用

        // ============ 状态图标时间戳追踪 ============
        const now = Date.now();
        const stateTimestamps = npcStateTimestampsRef.current;
        const npcName = npc.name;

        // 初始化 NPC 状态追踪
        if (!stateTimestamps[npcName]) {
          stateTimestamps[npcName] = {
            walkModeStarted: null,
            idleStarted: now,
            lastWalkMode: 'idle',
          };
        }

        const npcState = stateTimestamps[npcName];
        const currentWalkMode = (npc as any).walk_mode || 'idle';

        // 检测走路模式变化
        if (currentWalkMode !== npcState.lastWalkMode) {
          if (currentWalkMode !== 'idle' && currentWalkMode !== undefined) {
            // 进入走路模式
            npcState.walkModeStarted = now;
            npcState.idleStarted = null;
          } else {
            // 进入静止状态
            npcState.idleStarted = now;
            npcState.walkModeStarted = null;
          }
          npcState.lastWalkMode = currentWalkMode;
        }

        // 计算状态图标显示
        let statusIcon: string | null = null;
        const WALK_ICON_DURATION = 1000;  // 走路图标显示 1 秒
        const IDLE_ICON_DURATION = 2000;  // 静止图标显示 2 秒

        if (isTalking) {
          // 说话状态优先级最高
          statusIcon = 'talking';
        } else if (npcState.walkModeStarted && (now - npcState.walkModeStarted) < WALK_ICON_DURATION) {
          // 走路模式开始后 1 秒内
          statusIcon = 'walking';
        } else if (npcState.idleStarted && (now - npcState.idleStarted) < IDLE_ICON_DURATION) {
          // 静止状态开始后 2 秒内
          statusIcon = 'thinking';
        }

        // 禁用状态的透明度和灰度
        const opacity = isEnabled ? 1 : 0.4;
        const grayscale = isEnabled ? 0 : 0.5;

        // 选中光晕 (RPG 风格地面光环)
        if (isSelected) {
          const selPulse = 0.8 + Math.sin(Date.now() / 400) * 0.2;
          const selRadius = 12 * renderScale * selPulse;
          // 外圈光晕
          const selGlow = ctx.createRadialGradient(x, y - 2 * renderScale, 0, x, y - 2 * renderScale, selRadius);
          selGlow.addColorStop(0, 'rgba(251, 191, 36, 0.25)');
          selGlow.addColorStop(0.6, 'rgba(251, 191, 36, 0.08)');
          selGlow.addColorStop(1, 'transparent');
          ctx.fillStyle = selGlow;
          ctx.beginPath();
          ctx.arc(x, y - 2 * renderScale, selRadius, 0, Math.PI * 2);
          ctx.fill();
          // 地面选中环 (椭圆)
          ctx.strokeStyle = `rgba(251, 191, 36, ${0.4 + Math.sin(Date.now() / 300) * 0.2})`;
          ctx.lineWidth = Math.max(1, 1.5 * renderScale);
          ctx.beginPath();
          ctx.ellipse(x, y - 3 * renderScale, 8 * renderScale, 4 * renderScale, 0, 0, Math.PI * 2);
          ctx.stroke();
        }

        // 精灵图尺寸 (根据精灵 ID 动态解析)
        const spriteId = (npc as any).sprite_id || 'Adam';
        const layout = resolveSpriteLayout(spriteId);
        const spriteDrawWidth = layout.drawWidth * renderScale;
        const spriteDrawHeight = layout.drawHeight * renderScale;
        const sprite = sprites[layout.assetId];

        if (sprite) {
          // 绘制阴影 (柔和椭圆阴影，偏移模拟光源方向)
          const shadowRadius = layout.drawWidth * 0.3 * renderScale;
          // 外层模糊阴影
          ctx.fillStyle = 'rgba(0, 0, 0, 0.12)';
          ctx.beginPath();
          ctx.ellipse(x + 1, y - 3 * renderScale, shadowRadius * 1.3, shadowRadius * 0.5, 0, 0, Math.PI * 2);
          ctx.fill();
          // 内层实心阴影
          ctx.fillStyle = 'rgba(0, 0, 0, 0.22)';
          ctx.beginPath();
          ctx.ellipse(x, y - 4 * renderScale, shadowRadius, shadowRadius * 0.4, 0, 0, Math.PI * 2);
          ctx.fill();

          // 保存当前上下文状态
          ctx.save();

          // 应用禁用状态的透明度和灰度
          if (!isEnabled) {
            ctx.globalAlpha = opacity;
            ctx.filter = `grayscale(${grayscale * 100}%)`;
          }

          // 根据移动方向和行走状态计算源矩形
          // 上帝控制的 NPC: 优先使用键盘方向，其次使用保存的最后方向，最后回退到后端方向
          const isGodControlled = (npc as any).god_controlled;
          const isSelectedNPC = npc.name === selectedNPC;

          let direction: string;
          if (isGodControlled && isSelectedNPC) {
            if (godDirection) {
              // 有键盘输入时，更新保存的方向
              godLastDirectionRef.current = godDirection;
              direction = godDirection;
            } else if (godLastDirectionRef.current) {
              // 没有键盘输入但仍在控制，使用保存的最后方向
              direction = godLastDirectionRef.current;
            } else {
              // 没有保存的方向，使用后端方向或默认
              direction = (npc as any).god_move_direction || 'down';
            }
          } else {
            // 不受上帝控制，使用后端方向或默认
            direction = (npc as any).god_move_direction || 'down';
          }

          const walkMode = (npc as any).walk_mode;
          // 上帝控制的 NPC: 有方向输入时显示行走动画
          // 其他 NPC: walkMode 不是 idle 时显示行走动画
          const isGodMoving = isGodControlled && isSelectedNPC && godDirection;
          const isAutoMoving = walkMode !== 'idle' && walkMode !== undefined;
          const isMoving = isGodMoving || isAutoMoving;

          let sourceX = 0;
          let sourceY = 0;

          if (isMoving) {
            // 行走动画: 使用 delta time 计算帧索引 (更平滑)
            const walkStart = WALK_START_MAP[direction] ?? 18;
            const frameIndex = Math.floor(frameTimer / frameInterval) % 6;
            sourceX = (walkStart + frameIndex) * layout.frameWidth;
            sourceY = layout.walkRowY;  // 行走动画在第二行
          } else {
            // 静止帧: 使用 IDLE_FRAME_MAP
            const idleFrame = IDLE_FRAME_MAP[direction] ?? 3;
            sourceX = idleFrame * layout.frameWidth;
            sourceY = 0;  // 静止帧在第一行
          }

          // 绘制坐标取整 (避免亚像素抖动)
          const drawX = Math.round(x - spriteDrawWidth / 2);
          const drawY = Math.round(y - spriteDrawHeight);

          // 绘制精灵图 (使用 9 参数 drawImage 裁剪帧)
          ctx.drawImage(
            sprite,
            sourceX, sourceY, layout.frameWidth, layout.frameHeight,  // 源矩形
            drawX, drawY,                                              // 目标 X, Y (取整)
            spriteDrawWidth,                                           // 目标宽度
            spriteDrawHeight                                           // 目标高度
          );

          // 玩家边框
          if (isPlayer) {
            ctx.strokeStyle = '#38bdf8';
            ctx.lineWidth = 2;
            ctx.strokeRect(
              x - spriteDrawWidth / 2 - 2,
              y - spriteDrawHeight - 2,
              spriteDrawWidth + 4,
              spriteDrawHeight + 4
            );
          }

          // 选中边框
          if (isSelected) {
            ctx.strokeStyle = '#fbbf24';
            ctx.lineWidth = 2;
            ctx.strokeRect(
              x - spriteDrawWidth / 2 - 1,
              y - spriteDrawHeight - 1,
              spriteDrawWidth + 2,
              spriteDrawHeight + 2
            );
          }

          // 恢复上下文状态
          ctx.restore();
        } else {
          // 降级: 使用圆点
          const radius = isPlayer ? 14 : isSelected ? 12 : 10;

          ctx.save();
          if (!isEnabled) {
            ctx.globalAlpha = opacity;
          }

          ctx.beginPath();
          ctx.arc(x, y, radius, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();

          if (isPlayer) {
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 3;
            ctx.stroke();
          }
          ctx.restore();
        }

        // 对话动画效果 (柔和脉动光晕)
        if (isTalking) {
          const talkPulse = 0.7 + Math.sin(Date.now() / 250) * 0.3;
          const talkRadius = (spriteDrawWidth / 2 + 6) * talkPulse;
          const talkGlow = ctx.createRadialGradient(
            x, y - spriteDrawHeight / 2, talkRadius * 0.3,
            x, y - spriteDrawHeight / 2, talkRadius
          );
          talkGlow.addColorStop(0, `rgba(74, 222, 128, ${0.15 * talkPulse})`);
          talkGlow.addColorStop(1, 'transparent');
          ctx.fillStyle = talkGlow;
          ctx.beginPath();
          ctx.arc(x, y - spriteDrawHeight / 2, talkRadius, 0, Math.PI * 2);
          ctx.fill();
        }

        // ============ 收集头顶状态图标数据 (用 HTML 覆盖层显示 GIF 动画) ============
        if (statusIcon) {
          // 48x48 素材，显示尺寸按 24 算
          const iconSize = 24 * renderScale;
          iconOverlays.push({
            npcName: npc.name,
            iconType: statusIcon,
            iconSize,
            screenX: Math.round(x - iconSize / 2),
            // 图标底部往下移，覆盖到精灵图顶部的透明区域
            screenY: Math.round(y - spriteDrawHeight - iconSize + 14 * renderScale),
          });
        }

        // ============ 名字标签 (像素风名牌) ============
        ctx.font = '8px "Press Start 2P", monospace';
        ctx.textAlign = 'center';
        const npcNameWidth = ctx.measureText(npc.name).width;
        const nameTagY = y - spriteDrawHeight - 10;

        // 名牌背景
        ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
        const nPad = 3;
        ctx.fillRect(x - npcNameWidth / 2 - nPad, nameTagY - 8, npcNameWidth + nPad * 2, 11);

        // 名牌底色条 (颜色标识)
        ctx.fillStyle = color + '40';
        ctx.fillRect(x - npcNameWidth / 2 - nPad, nameTagY - 8, npcNameWidth + nPad * 2, 11);

        // 名字文字
        ctx.fillStyle = color;
        ctx.fillText(npc.name, x, nameTagY);

        // 状态标签
        if (!isEnabled) {
          ctx.fillStyle = '#6b7280';
          ctx.font = '7px "Press Start 2P", monospace';
          ctx.fillText('[禁用]', x, nameTagY - 13);
        } else if (isSelected) {
          ctx.fillStyle = '#fbbf24';
          ctx.font = '7px "Press Start 2P", monospace';
          ctx.fillText('[控制中]', x, nameTagY - 13);
        } else if (isPlayer) {
          ctx.fillStyle = '#38bdf8';
          ctx.font = '7px "Press Start 2P", monospace';
          ctx.fillText('[玩家]', x, nameTagY - 13);
        }
      });

      // 更新状态图标覆盖层
      setStatusIconOverlays(iconOverlays);

      // ============ 后处理: 暗角 (Vignette) ============
      const vignetteGradient = ctx.createRadialGradient(
        width / 2, height / 2, Math.min(width, height) * 0.3,
        width / 2, height / 2, Math.max(width, height) * 0.75
      );
      vignetteGradient.addColorStop(0, 'transparent');
      vignetteGradient.addColorStop(0.7, 'rgba(0, 0, 0, 0.08)');
      vignetteGradient.addColorStop(1, 'rgba(0, 0, 0, 0.3)');
      ctx.fillStyle = vignetteGradient;
      ctx.fillRect(0, 0, width, height);

      // ============ 精致小地图 (独立 DOM canvas，置于 GIF 覆盖层之上，不被贴图遮挡) ============
      const mmCanvas = miniMapCanvasRef.current;
      if (mmCanvas) {
        const mmCtx = mmCanvas.getContext('2d');
        if (mmCtx) {
          mmCtx.imageSmoothingEnabled = false;
          const miniMapSize = 110;
          const miniMapPad = 4;  // 内边距
          const boxY = 14;       // 地图区在画布内的 y (顶部留给标题)
          mmCtx.clearRect(0, 0, mmCanvas.width, mmCanvas.height);

          // 小地图标题
          mmCtx.font = '6px "Press Start 2P", monospace';
          mmCtx.fillStyle = '#8888aa';
          mmCtx.textAlign = 'left';
          mmCtx.fillText('MAP', 4, 9);

          // 小地图外框阴影
          mmCtx.fillStyle = 'rgba(0, 0, 0, 0.4)';
          mmCtx.fillRect(3, boxY + 3, miniMapSize, miniMapSize);

          // 小地图背景 (深色 + 地面色)
          mmCtx.fillStyle = '#0d0d18';
          mmCtx.fillRect(0, boxY, miniMapSize, miniMapSize);

          // 小地图地面纹理
          mmCtx.fillStyle = '#14141e';
          mmCtx.fillRect(miniMapPad, boxY + miniMapPad,
            miniMapSize - miniMapPad * 2, miniMapSize - miniMapPad * 2);

          const mmInner = miniMapSize - miniMapPad * 2;

          // 小地图上的障碍物
          obstacles.forEach(obs => {
            if (obs.type === 'rect') {
              const mmX = miniMapPad + (obs.x / MAP_WIDTH) * mmInner;
              const mmY = boxY + miniMapPad + (obs.y / MAP_HEIGHT) * mmInner;
              const mmW = Math.max(1, ((obs.width || 0) / MAP_WIDTH) * mmInner);
              const mmH = Math.max(1, ((obs.height || 0) / MAP_HEIGHT) * mmInner);
              mmCtx.fillStyle = '#3a2a1a';
              mmCtx.fillRect(mmX, mmY, mmW, mmH);
            } else if (obs.type === 'circle') {
              const mmX = miniMapPad + (obs.x / MAP_WIDTH) * mmInner;
              const mmY = boxY + miniMapPad + (obs.y / MAP_HEIGHT) * mmInner;
              const mmR = Math.max(1, ((obs.radius || 5) / MAP_WIDTH) * mmInner);
              mmCtx.beginPath();
              mmCtx.arc(mmX, mmY, mmR, 0, Math.PI * 2);
              mmCtx.fillStyle = obs.desc?.includes('树') ? '#1a4a18' : '#3a3a3a';
              mmCtx.fill();
            }
          });

          // 小地图上的地点 (带光晕)
          locations.forEach(loc => {
            const mmX = miniMapPad + (loc.x / MAP_WIDTH) * mmInner;
            const mmY = boxY + miniMapPad + (loc.y / MAP_HEIGHT) * mmInner;
            const lColor = LOCATION_COLORS[loc.name] || '#e879f9';

            // 地点光晕
            const mmGlow = mmCtx.createRadialGradient(mmX, mmY, 0, mmX, mmY, 6);
            mmGlow.addColorStop(0, lColor + '50');
            mmGlow.addColorStop(1, 'transparent');
            mmCtx.fillStyle = mmGlow;
            mmCtx.beginPath();
            mmCtx.arc(mmX, mmY, 6, 0, Math.PI * 2);
            mmCtx.fill();

            // 地点方块
            mmCtx.fillStyle = lColor;
            mmCtx.fillRect(mmX - 1.5, mmY - 1.5, 3, 3);
          });

          // 小地图上的 NPC (带方向指示)
          npcs.forEach((npc, index) => {
            const mmX = miniMapPad + (npc.x / MAP_WIDTH) * mmInner;
            const mmY = boxY + miniMapPad + (npc.y / MAP_HEIGHT) * mmInner;
            const nColor = COLORS[index % COLORS.length];
            const isSelMM = npc.name === selectedNPC;

            if (isSelMM) {
              // 选中 NPC 有脉动效果
              const mmPulse = 1 + Math.sin(Date.now() / 300) * 0.3;
              mmCtx.beginPath();
              mmCtx.arc(mmX, mmY, 3 * mmPulse, 0, Math.PI * 2);
              mmCtx.fillStyle = nColor + '80';
              mmCtx.fill();
            }

            mmCtx.fillStyle = nColor;
            mmCtx.fillRect(mmX - 1, mmY - 1, 2, 2);
          });

          // 小地图上的视口框 (钳制在小地图范围内; 地图小于视口时框=整框)
          mmCtx.strokeStyle = '#fbbf24';
          mmCtx.lineWidth = 1;
          const vpW = Math.min(mmInner, Math.max(2, (actualViewWidth / MAP_WIDTH) * mmInner));
          const vpH = Math.min(mmInner, Math.max(2, (actualViewHeight / MAP_HEIGHT) * mmInner));
          const vpX = Math.max(miniMapPad, Math.min(miniMapPad + mmInner - vpW,
            miniMapPad + (minX / MAP_WIDTH) * mmInner));
          const vpY = Math.max(boxY + miniMapPad, Math.min(boxY + miniMapPad + mmInner - vpH,
            boxY + miniMapPad + (minY / MAP_HEIGHT) * mmInner));
          mmCtx.strokeRect(vpX, vpY, vpW, vpH);

          // 小地图像素边框 (双线)
          mmCtx.strokeStyle = '#3a3a5a';
          mmCtx.lineWidth = 2;
          mmCtx.strokeRect(0, boxY, miniMapSize, miniMapSize);
          mmCtx.strokeStyle = '#5a5a7a';
          mmCtx.lineWidth = 1;
          mmCtx.strokeRect(1, boxY + 1, miniMapSize - 2, miniMapSize - 2);
        }
      }

      // 继续下一帧
      animationId = requestAnimationFrame(render);
    };

    // 启动渲染循环
    animationId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [dimensions, locations, obstacles, sprites, tiles, tileImages, buildingImages, isDragging]);

  // 点击检测
  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    // 如果发生了拖动，不触发点击
    if (hasMoved) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const { width, height } = dimensions;
    const viewport = viewportRef.current;
    const npcs = npcsRef.current;
    const currentScale = scaleRef.current;

    // 计算视口范围 - 与 render 函数一致
    const baseViewSize = MAP_WIDTH / VIEWPORT_SCALE;
    const renderScale = Math.min(width, height) / baseViewSize * currentScale;
    const viewWidth = width / renderScale;
    const viewHeight = height / renderScale;

    // 与渲染循环一致: 不做 0/MAP 钳制 (地图小于视口时居中)
    const minX = viewport.x - viewWidth / 2;
    const maxX = viewport.x + viewWidth / 2;
    const minY = viewport.y - viewHeight / 2;
    const maxY = viewport.y + viewHeight / 2;

    const actualViewWidth = maxX - minX;
    const actualViewHeight = maxY - minY;

    // 画布坐标转地图坐标
    const canvasToMap = (cx: number, cy: number) => ({
      x: minX + (cx / width) * actualViewWidth,
      y: minY + (cy / height) * actualViewHeight,
    });

    const { x: mapX, y: mapY } = canvasToMap(clickX, clickY);

    // 查找点击的 NPC
    for (const npc of npcs) {
      const distance = Math.sqrt((mapX - npc.x) ** 2 + (mapY - npc.y) ** 2);
      if (distance < 5) {
        onNPCClick?.(npc.name);
        break;
      }
    }
  };

  // 滚轮缩放 - 以鼠标位置为中心
  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();

    // 标记正在缩放，暂停追踪
    setIsZooming(true);
    if (zoomTimeoutRef.current) {
      clearTimeout(zoomTimeoutRef.current);
    }

    const canvas = canvasRef.current;
    if (!canvas || dimensions.width === 0) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // 计算鼠标在地图上的位置 (缩放前)
    const { width, height } = dimensions;
    const currentScale = scaleRef.current;
    const viewport = viewportRef.current;

    const baseViewSize = MAP_WIDTH / VIEWPORT_SCALE;
    const renderScale = Math.min(width, height) / baseViewSize * currentScale;
    const viewWidth = width / renderScale;
    const viewHeight = height / renderScale;

    // 与渲染循环一致: 不做 0/MAP 钳制 (地图小于视口时居中)
    const minX = viewport.x - viewWidth / 2;
    const maxX = viewport.x + viewWidth / 2;
    const minY = viewport.y - viewHeight / 2;
    const maxY = viewport.y + viewHeight / 2;

    const mouseMapX = minX + (mouseX / width) * (maxX - minX);
    const mouseMapY = minY + (mouseY / height) * (maxY - minY);

    // 计算新缩放 (下限为动态的"整图撑满画布")
    const delta = e.deltaY > 0 ? -SCALE_STEP : SCALE_STEP;
    const newScale = Math.max(getMinScale(), Math.min(MAX_SCALE, currentScale + delta));

    // 计算缩放后的视口位置 (保持鼠标位置不变)
    const newRenderScale = Math.min(width, height) / baseViewSize * newScale;
    const newViewWidth = width / newRenderScale;
    const newViewHeight = height / newRenderScale;

    // 新视口中心 = 鼠标地图位置 - (鼠标画布位置比例 - 0.5) * 视口尺寸
    const newViewportX = mouseMapX - (mouseX / width - 0.5) * newViewWidth;
    const newViewportY = mouseMapY - (mouseY / height - 0.5) * newViewHeight;

    // 边界限制 (视口大于等于地图时居中)
    const clampedViewportX = newViewWidth >= MAP_WIDTH ? MAP_WIDTH / 2
      : Math.max(newViewWidth / 2, Math.min(MAP_WIDTH - newViewWidth / 2, newViewportX));
    const clampedViewportY = newViewHeight >= MAP_HEIGHT ? MAP_HEIGHT / 2
      : Math.max(newViewHeight / 2, Math.min(MAP_HEIGHT - newViewHeight / 2, newViewportY));

    // 更新视口和缩放
    viewportRef.current = { x: clampedViewportX, y: clampedViewportY };
    setScale(newScale);

    // 更新 manualOffset (这样缩放后不会弹回去)
    // 使用统一函数获取相机目标
    const npcs = npcsRef.current;
    const selectedNPC = selectedNPCRef.current;
    const renderPositions = renderPositionsRef.current;
    const { x: targetX, y: targetY } = getCameraTargetPosition(npcs, selectedNPC, renderPositions);

    const newOffset = {
      x: clampedViewportX - targetX,
      y: clampedViewportY - targetY,
    };
    setManualOffset(newOffset);
    manualOffsetRef.current = newOffset;

    // 延迟恢复追踪 (500ms 后)
    zoomTimeoutRef.current = setTimeout(() => {
      setIsZooming(false);
    }, 500);
  };

  // 拖动开始
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (e.button === 0) { // 左键
      setIsDragging(true);
      setHasMoved(false); // 重置移动标记
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  // 拖动中
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging) return;

    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;

    // 检查是否超过拖动阈值
    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance > DRAG_THRESHOLD) {
      setHasMoved(true);
    }

    // 只有真正移动了才更新视口
    if (distance < 1) return;

    // 计算地图坐标偏移 (考虑当前缩放)
    const currentScale = scaleRef.current;
    const { width, height } = dimensions;
    const baseViewSize = MAP_WIDTH / VIEWPORT_SCALE;
    const renderScale = Math.min(width, height) / baseViewSize * currentScale;

    // 转换为地图坐标偏移
    const mapDx = -dx / renderScale;
    const mapDy = -dy / renderScale;

    // 计算视口尺寸 (用于边界限制)
    const viewWidth = width / renderScale;
    const viewHeight = height / renderScale;

    // 更新视口并限制在地图边界内
    const newX = viewportRef.current.x + mapDx;
    const newY = viewportRef.current.y + mapDy;

    // 视口中心不能超出地图边界 (考虑视口尺寸)
    const minX = viewWidth / 2;
    const maxX = MAP_WIDTH - viewWidth / 2;
    const minY = viewHeight / 2;
    const maxY = MAP_HEIGHT - viewHeight / 2;

    viewportRef.current.x = Math.max(minX, Math.min(maxX, newX));
    viewportRef.current.y = Math.max(minY, Math.min(maxY, newY));

    setDragStart({ x: e.clientX, y: e.clientY });
  };

  // 结束拖动并保存偏移量
  const finishDrag = () => {
    if (!isDragging) return;

    // 计算当前视口与目标的偏差，作为新的 manualOffset
    // 使用统一函数获取相机目标
    const npcs = npcsRef.current;
    const selectedNPC = selectedNPCRef.current;
    const renderPositions = renderPositionsRef.current;
    const { x: targetX, y: targetY } = getCameraTargetPosition(npcs, selectedNPC, renderPositions);

    // manualOffset = 视口位置 - 目标位置
    const newOffset = {
      x: viewportRef.current.x - targetX,
      y: viewportRef.current.y - targetY,
    };
    setManualOffset(newOffset);
    manualOffsetRef.current = newOffset;

    setIsDragging(false);
  };

  // 拖动结束
  const handleMouseUp = () => {
    finishDrag();
  };

  // 鼠标离开 - 也要保存偏移量
  const handleMouseLeave = () => {
    finishDrag();
  };

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        background: 'var(--bg-deep)',
        borderRadius: 8,
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <canvas
        ref={canvasRef}
        width={dimensions.width}
        height={dimensions.height}
        onClick={handleClick}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
      />
      {/* 障碍物 GIF 覆盖层 (随机动画: 5-10秒触发一次，播放2-3秒) */}
      {obstacleOverlays.map(({ id, sprite, screenX, screenY, size }) => {
        const isAnimating = animatingObstacles.has(id);
        const staticFrame = obstacleStaticFramesRef.current[id];

        return (
          <img
            key={id}
            src={isAnimating ? sprite : (staticFrame || sprite)}
            alt={id}
            onLoad={(e) => {
              // 首次加载时捕获第一帧作为静态图
              if (!obstacleStaticFramesRef.current[id]) {
                const img = e.currentTarget;
                const canvas = document.createElement('canvas');
                canvas.width = img.naturalWidth;
                canvas.height = img.naturalHeight;
                const ctx = canvas.getContext('2d');
                if (ctx) {
                  ctx.imageSmoothingEnabled = false;
                  ctx.drawImage(img, 0, 0);
                  obstacleStaticFramesRef.current[id] = canvas.toDataURL('image/png');
                }
              }
            }}
            style={{
              position: 'absolute',
              left: screenX,
              top: screenY,
              width: size,
              height: size,
              pointerEvents: 'none',
              imageRendering: 'pixelated',
            }}
          />
        );
      })}
      {/* 状态图标覆盖层 (GIF 动画) */}
      {statusIconOverlays.map(({ npcName, iconType, screenX, screenY, iconSize }) => {
        const iconFile = iconType === 'talking'
          ? 'UI_mail_48x48.gif'
          : iconType === 'walking'
          ? 'UI_timer_green_to_green_48x48.gif'
          : 'UI_thinking_emote_dots_48x48.gif';
        return (
          <img
            key={npcName}
            src={`/ui/${iconFile}`}
            alt={iconType}
            style={{
              position: 'absolute',
              left: screenX,
              top: screenY,
              width: iconSize,
              height: iconSize,
              pointerEvents: 'none',
              imageRendering: 'pixelated',
            }}
          />
        );
      })}
      {/* 小地图 (独立 canvas，置于所有覆盖层之上，不遮挡主画布交互) */}
      <canvas
        ref={miniMapCanvasRef}
        width={110}
        height={127}
        style={{
          position: 'absolute',
          right: 14,
          bottom: 14,
          pointerEvents: 'none',
          zIndex: 10,
        }}
      />
    </div>
  );
}
