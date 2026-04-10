# 精灵图系统 Skill

---
description: 精灵图规格、动画布局、方向映射与前后端配置
triggers:
  - 添加新角色精灵图
  - 修改精灵图渲染逻辑
  - 处理角色方向/动画问题
  - 上帝模式移动渲染
---

## 1. 双规格支持

系统支持两种精灵图规格，渲染尺寸统一为 16x24：

| 规格 | 帧尺寸 | 渲染尺寸 | 文件后缀 | 行走动画 Y |
|------|--------|----------|----------|------------|
| **16x16** | 16 x 32 | 16 x 24 | `_16x16.png` | 32 |
| **48x48** | 48 x 96 | 16 x 24 (缩小3倍) | `_48x48.png` | 96 |

---

## 2. 帧布局规则 (两种规格通用)

### 2.1 Row 0: 静止站立 (4帧)

| 帧索引 | 0 | 1 | 2 | 3 |
|--------|---|---|---|---|
| 方向 | 右 | 后(上) | 左 | 前(下) |

### 2.2 Row 1: 行走动画 (24帧 = 4方向 × 6帧)

| 方向 | 帧范围 | 起始偏移 |
|------|--------|----------|
| 右 (right) | 0-5 | 0 |
| 后/上 (up) | 6-11 | 6 |
| 左 (left) | 12-17 | 12 |
| 前/下 (down) | 18-23 | 18 |

---

## 3. 精灵名称映射

前端 UI 使用友好名称显示精灵，配置文件: `static/src/config/sprites.ts`

```typescript
// 精灵 ID -> 友好名称
const SPRITE_NAMES: Record<string, string> = {
  // 16x 基础角色
  'Adam': '亚当 (16x)',
  'Alex': '亚历克斯 (16x)',
  // ...
  // 48x 高清角色
  'Scout_1_48x48': '侦察兵 A (48x)',
  'Skeleton_1_48x48': '骷髅 (48x)',
  // ...
};

// Select 组件使用
options={spriteIdsToOptions(sprites)}  // 自动分组
```

### 添加新精灵时

同步更新 `static/src/config/sprites.ts` 中的 `SPRITE_NAMES` 映射。

---

## 4. 前端渲染核心代码

```typescript
// static/src/components/Map/MapView.tsx

interface SpriteLayout {
  frameWidth: number;    // 单帧宽度
  frameHeight: number;   // 单帧高度 (是宽度的2倍)
  drawWidth: number;     // 渲染宽度
  drawHeight: number;    // 渲染高度
  assetId: string;       // 资源 ID
  walkRowY: number;      // 行走动画行的 Y 坐标
}

// 方向到帧索引的映射
const IDLE_FRAME_MAP: Record<string, number> = {
  right: 0, up: 1, left: 2, down: 3,
};

const WALK_START_MAP: Record<string, number> = {
  right: 0, up: 6, left: 12, down: 18,
};

function resolveSpriteLayout(spriteId?: string): SpriteLayout {
  const rawId = spriteId || 'Adam';
  if (rawId.endsWith('_48x48')) {
    return {
      frameWidth: 48, frameHeight: 96,
      drawWidth: 16, drawHeight: 24,  // 缩小到统一尺寸
      assetId: rawId, walkRowY: 96,
    };
  }
  return {
    frameWidth: 16, frameHeight: 32,
    drawWidth: 16, drawHeight: 24,
    assetId: rawId, walkRowY: 32,
  };
}
```

### 渲染优化

```typescript
// 1. 禁用图像平滑，保持像素清晰
ctx.imageSmoothingEnabled = false;

// 2. Delta time 帧动画 (更平滑)
frameTimer += delta;
const frameIndex = Math.floor(frameTimer / frameInterval) % 6;

// 3. 坐标取整，避免亚像素抖动
const drawX = Math.round(x - spriteDrawWidth / 2);
const drawY = Math.round(y - spriteDrawHeight);
```

---

## 5. 上帝模式移动渲染

### 5.1 客户端位置插值

```typescript
// 存储每个 NPC 的渲染位置 (平滑过渡)
const renderPositionsRef = useRef<Record<string, { x: number; y: number }>>({});
const godLastDirectionRef = useRef<string | null>(null);  // 保留最后方向

// 更新渲染位置
npcs.forEach(npc => {
  if (!renderPositions[npc.name]) {
    renderPositions[npc.name] = { x: npc.x, y: npc.y };
  }

  if ((npc as any).god_controlled) {
    // 上帝控制: 完全客户端预测，忽略后端位置
    if (godDirection) {
      const speed = GOD_MOVE_SPEED;  // 60 像素/秒
      // ... 根据 direction 更新位置
      rp.x = Math.max(0, Math.min(MAP_WIDTH, rp.x + dx * delta));
    }
    // 无方向时保持当前位置
  } else {
    // 其他 NPC: 向真实位置插值
    rp.x += (npc.x - rp.x) * POSITION_LERP_FACTOR;  // 0.15
    rp.y += (npc.y - rp.y) * POSITION_LERP_FACTOR;
  }
});
```

### 5.2 方向保留逻辑

```typescript
// 上帝控制的 NPC: 优先键盘方向，其次保存的最后方向
if (isGodControlled && isSelectedNPC) {
  if (godDirection) {
    godLastDirectionRef.current = godDirection;  // 保存方向
    direction = godDirection;
  } else if (godLastDirectionRef.current) {
    direction = godLastDirectionRef.current;  // 使用保存的方向
  } else {
    direction = npc.god_move_direction || 'down';  // 回退
  }
}

// 行走动画判断
const isGodMoving = isGodControlled && isSelectedNPC && godDirection;
const isAutoMoving = walkMode !== 'idle' && walkMode !== undefined;
const isMoving = isGodMoving || isAutoMoving;
```

### 5.3 Store 中的方向管理

```typescript
// static/src/store/useGodStore.ts
export const godMoveDirectionRef = { current: null as string | null };

move: async (direction) => {
  godMoveDirectionRef.current = direction;  // 立即设置 (客户端预测)
  await godApi.move(direction);
},

stop: async () => {
  godMoveDirectionRef.current = null;  // 立即清除
  await godApi.stop();
},

deselectNPC: async () => {
  godMoveDirectionRef.current = null;  // 取消控制时清除
  set({ selectedNPC: null, isGodMode: false });
},
```

---

## 6. 方向映射注意事项

⚠️ **重要**: 精灵图的方向顺序是 `右、后、左、前`，不是常见的 `上、下、左、右`

- `up` (地图向上) = 角色**背面** = 精灵图索引 1/6-11
- `down` (地图向下) = 角色**正面** = 精灵图索引 3/18-23

---

## 7. 后端 NPC 方向字段

```python
# body/npc.py
self.god_move_direction = None   # 'up' | 'down' | 'left' | 'right' | None
self.walk_mode = 'random'        # 'idle' | 'random' | 'linear' | 'to_target'
```

---

## 8. 精灵图加载机制

```typescript
// 优先从 API 获取精灵列表，失败则使用默认列表
fetch('/api/sprites')
  .then(res => res.json())
  .then(data => {
    if (data.status === 'ok' && Array.isArray(data.sprites)) {
      loadSprites(data.sprites);  // 动态加载
    } else {
      loadSprites(defaultSpriteIds);  // 回退默认
    }
  });

// 根据 ID 后缀决定文件名
const fileName = id.endsWith('_48x48') ? id : `${id}_16x16`;
img.src = `/sprites/${fileName}.png`;
```

后端 API (`/api/sprites`) 会扫描 `static/public/sprites/` 目录，返回所有 `*_16x16.png` 和 `*_48x48.png` 文件。

---

## 9. 添加新精灵图的步骤

### 9.1 16x16 规格

1. 准备精灵图：768 x 288 像素，48列 × 9行
2. 命名：`{Name}_16x16.png`
3. 放入：`static/public/sprites/`
4. 更新 `static/src/config/sprites.ts` 添加名称映射
5. 后端自动扫描，无需手动注册

### 9.2 48x48 规格

1. 准备精灵图：帧尺寸 48x96，布局与 16x16 相同
2. 命名：`{Name}_48x48.png`
3. 放入：`static/public/sprites/`
4. 更新 `static/src/config/sprites.ts` 添加名称映射
5. 在 NPC 配置中设置 `sprite_id: "{Name}_48x48"`

---

## 10. 已有精灵列表

### 16x16 规格
| ID | 友好名称 |
|----|----------|
| Adam | 亚当 |
| Alex | 亚历克斯 |
| Amelia | 阿米莉亚 |
| Ash | 艾什 |
| Bob | 鲍勃 |
| Bruce | 布鲁斯 |
| Dan | 丹 |
| Edward | 爱德华 |
| Lucy | 露西 |
| Molly | 莫莉 |

### 48x48 规格
| ID | 友好名称 |
|----|----------|
| Postman_1_48x48 | 邮递员 A |
| Postman_2_48x48 | 邮递员 B |
| Postman_3_48x48 | 邮递员 C |
| Scout_1_48x48 | 侦察兵 A |
| Scout_2_48x48 | 侦察兵 B |
| Scout_3_48x48 | 侦察兵 C |
| Scout_4_48x48 | 侦察兵 D |
| Scout_5_48x48 | 侦察兵 E |
| Scout_6_48x48 | 侦察兵 F |
| Skeleton_1_48x48 | 骷髅 |
| Swimmers_48x48 | 游泳者 |
| Zombie_1_48x48 | 僵尸 A |
| Zombie_2_48x48 | 僵尸 B |

---

## 11. 头顶状态图标

### 11.1 素材规格

| 状态 | 图标文件 | 触发条件 | 显示时长 |
|------|----------|----------|----------|
| 说话 | `UI_mail_48x48.gif` | `npc.is_talking === true` | 持续显示 |
| 走路 | `UI_timer_green_to_green_48x48.gif` | 进入走路模式 | 1 秒 |
| 思考 | `UI_thinking_emote_dots_48x48.gif` | 进入静止状态 | 2 秒 |

素材目录：`static/public/ui/`

### 11.2 渲染配置

```typescript
// 48x48 素材，显示尺寸按 24 算
const iconSize = 24 * renderScale;

// 位置计算
screenX: x - iconSize / 2,  // 水平居中
screenY: y - spriteDrawHeight - iconSize + 14 * renderScale,  // 垂直位置
```

### 11.3 关键偏移量

⚠️ **精灵图顶部有透明区域**（为了凑正方形格子），图标需要下移覆盖到透明区域：

- **偏移量**: `14 * renderScale`
- **原因**: 精灵图帧尺寸是 16x32（或 48x96），但实际角色高度不足，顶部有约 14 像素的透明空白
- **效果**: 图标底部紧贴角色头部，而非精灵图边框

### 11.4 状态优先级

1. `is_talking` → 显示说话图标（最高优先级）
2. 走路模式开始后 1 秒内 → 显示走路图标
3. 静止状态开始后 2 秒内 → 显示思考图标

### 11.5 GIF 动画实现

使用 HTML `<img>` 元素叠加在 Canvas 上，浏览器自动播放 GIF 动画：

```tsx
{/* 状态图标覆盖层 */}
{statusIconOverlays.map(({ npcName, iconType, screenX, screenY, iconSize }) => (
  <img
    key={npcName}
    src={`/ui/${iconFile}`}
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
))}
```

⚠️ **Canvas drawImage 无法播放 GIF 动画**，必须使用 HTML 覆盖层。
