# NPC 移动状态机与工具流程文档

> 版本: v1.0
> 更新时间: 2026-02-18

---

## 1. walk_mode 状态流转

### 1.1 状态定义

| 状态值 | 含义 | NPC 行为 |
|--------|------|----------|
| `idle` | 闲置 | 不移动 |
| `random` | 随机漫步 | 随机方向小步移动 |
| `linear` | 直线行走 | 沿固定方向直线移动 |
| `to_target` | 前往目标 | 向指定坐标移动 (避障) |

### 1.2 状态字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `walk_mode` | str | 当前移动模式 |
| `walk_target` | tuple/None | 目标坐标 `(x, y)` |
| `walk_target_name` | str/None | 目标地点名称 (如 "酒馆") |
| `walk_mode_tick` | int | 模式计时器 (用于切换 random/linear) |
| `walk_direction` | float | 直线行走方向 (弧度) |
| `walk_random_duration` | int | 随机模式持续帧数 (NPC 属性) |
| `walk_linear_duration` | int | 直线模式持续帧数 (NPC 属性) |

### 1.3 状态流转图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         walk_mode 状态机                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   [初始状态]                                                          │
│       │                                                              │
│       ▼                                                              │
│   ┌──────────┐    goto_location工具    ┌────────────┐                │
│   │  idle    │ ──────────────────────► │ to_target  │                │
│   │ random   │                         │            │                │
│   │ linear   │ ◄────────────────────── │            │                │
│   └──────────┘     arrived_at工具       └────────────┘                │
│       ▲                                  │    │                       │
│       │                                  │    │ 到达坐标               │
│       │                                  │    ▼                       │
│       │                            ┌─────────────┐                   │
│       │                            │ 地点对话中   │                   │
│       │                            │ walk_target=None│               │
│       │                            │ walk_target_name=保留 │          │
│       │                            └─────────────┘                   │
│       │                                  │                           │
│       └──────────────────────────────────┘                           │
│                    arrived_at 调用后                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.4 关键时机

| 事件 | 触发时机 | 代码位置 |
|-----|---------|---------|
| `walk_mode = to_target` | goto_location 工具调用 | `tools/tool_l1.py:197` |
| `walk_target = (x,y)` | goto_location 工具调用 | `tools/tool_l1.py:198` |
| `walk_target_name = 地点名` | goto_location 工具调用 | `tools/tool_l1.py:199` |
| `walk_target = None` | 到达坐标时 (移动中) | `core/drive/drive_l1.py:50` |
| 触发地点对话 | 到达坐标且 walk_target_name 存在 | `core/drive/drive_l1.py:54-55` |
| `walk_mode = idle` | arrived_at 工具调用 | `tools/tool_l1.py:224` |
| `walk_target_name = None` | arrived_at 工具调用 | `tools/tool_l1.py:226` |
| 地点对话结束 | walk_target_name 变为 None | `core/social/social_l1.py:449-454` |

---

## 2. 移动工具流程

### 2.1 goto_location 工具

**功能**: 设置 NPC 前往指定地点

**代码位置**: `tools/tool_l1.py:170-203`

**参数**:
```json
{
  "location": "酒馆"  // 地点名称
}
```

**执行流程**:
```
1. 提取参数: location = "酒馆"
      │
      ▼
2. 查地点注册表: map.get_location_coords("酒馆") → (x, y)
      │
      ▼
3. 设置 NPC 状态:
   ├── npc.walk_mode = 'to_target'
   ├── npc.walk_target = (target_x, target_y)
   ├── npc.walk_target_name = "酒馆"
   └── npc.walk_mode_tick = 0
      │
      ▼
4. 返回: "开始前往 酒馆"
```

### 2.2 arrived_at 工具

**功能**: NPC 确认已到达目的地，清除移动状态

**代码位置**: `tools/tool_l1.py:206-230`

**参数**:
```json
{
  "location": "酒馆"  // 地点名称
}
```

**执行流程**:
```
1. 提取参数: location = "酒馆"
      │
      ▼
2. 清除 NPC 移动状态:
   ├── npc.walk_mode = 'idle'
   ├── npc.walk_target = None
   ├── npc.walk_target_name = None
   └── npc.walk_mode_tick = 0
      │
      ▼
3. 返回: "已到达 酒馆"
      │
      ▼
4. [social_l1.py:449] 检查 walk_target_name == None
   └─ 满足条件 → 地点对话循环 break
```

---

## 3. 移动与避障流程 (每帧)

### 3.1 主循环入口

**触发**: `main.py` 主循环调用 `drive.update_all()`

**代码位置**: `core/drive/drive_l1.py:10-133`

### 3.2 to_target 模式移动流程

**代码位置**: `core/drive/drive_l1.py:39-56` + `core/drive/drive_l2.py:107-184`

```
[drive_l1.py] update_drive_logic()
      │
      ▼
检查: walk_mode == 'to_target' and walk_target != None ?
      │
   ┌──┴──┐
   │ 是  │ 否 → 走 random/linear 闲逛逻辑
   ▼     │
[drive_l2.py] move_toward_target(x, y, tx, ty, step)
      │
      ▼
┌──────────────────────────────────────┐
│ 1. 计算距离 dist                      │
│    dist <= step_size ?                │
│    ├─ 是 → 检查目标是否被阻挡          │
│    │       ├─ 被阻挡 → 返回 (原位, arrived=False)│
│    │       └─ 未阻挡 → 返回 (目标坐标, arrived=True)│
│    │                                  │
│    └─ 否 → 继续移动                   │
│                                       │
│ 2. 沿方向移动一步                      │
│    new_x = x + dx * ratio             │
│    new_y = y + dy * ratio             │
│                                       │
│ 3. 障碍物碰撞检测                      │
│    map.is_blocked(new_x, new_y) ?     │
│    ├─ 未阻挡 → 返回 (new_x, new_y)     │
│    │                                  │
│    └─ 被阻挡 → 进入避障逻辑            │
│                                       │
│ 4. 避障绕行 (多策略)                   │
│    a. 找到阻挡的障碍物                 │
│    b. 计算绕行方向 (上下/左右/切线)    │
│    c. 尝试绕行方向移动                 │
│    d. 尝试反方向绕行                   │
│    e. 尝试垂直方向绕行                 │
│    f. 全被阻挡 → 保持原位              │
└──────────────────────────────────────┘
      │
      ▼
arrived == True ?
      │
   ┌──┴──┐
   │ 是  │ 否 → 更新坐标, 继续下一帧
   ▼     │
[drive_l1.py:45-55]
├─ 打印: "已到达目标坐标"
├─ walk_target = None  (清除坐标)
├─ walk_mode_tick = 0
└─ walk_target_name 存在?
     └─ 是 → _trigger_location_encounter(npc, location_name)
```

---

## 4. 避障寻路参数

### 4.1 避障策略优先级

| 优先级 | 策略 | 说明 |
|--------|------|------|
| 1 | 智能绕行 | 根据障碍物形状选择绕行方向 |
| 2 | 反方向绕行 | 尝试反向绕过障碍物 |
| 3 | 垂直绕行 | 沿垂直于目标方向移动 |

### 4.2 矩形障碍物绕行规则

```python
# map_l2.py:161-204
if obs_w > obs_h:
    # 横向墙 → 优先从上下绕
    return (0, 1) 或 (0, -1)
else:
    # 纵向墙 → 优先从左右绕
    return (1, 0) 或 (-1, 0)
```

### 4.3 圆形障碍物绕行规则

```python
# map_l2.py:206-226
# 选择切线方向绕行 (垂直于到圆心的方向)
# 选择与目标方向更一致的切线
tangent1 = (-to_y, to_x)   # 顺时针切线
tangent2 = (to_y, -to_x)   # 逆时针切线
```

---

## 5. 地点碰撞对话系统

### 5.1 触发条件

1. NPC 到达目标坐标 (`arrived == True`)
2. `walk_target_name` 非空
3. 不在冷却中 (`ban_target_uuid != "location:{地点名}"`)

### 5.2 对话流程

**代码位置**: `core/drive/drive_l1.py:135-169` + `core/social/social_l1.py:371-491`

```
[drive_l1.py] _trigger_location_encounter(npc, "酒馆")
      │
      ▼
1. 检查冷却锁: ban_target_uuid == "location:酒馆" ?
   └─ 是 → return (不重复触发)
      │
      ▼
2. 冻结 NPC: is_talking = True
      │
      ▼
3. 调用: social.run_location_encounter(npc, "酒馆")
   ┌────────────────────────────────────────────────┐
   │ [social_l1.py] run_location_conversation()     │
   │                                                │
   │ Round 1:                                       │
   │   ├─ 地点主动发言: "欢迎来到酒馆..."             │
   │   ├─ 存入 ram_buffer (role=user)               │
   │   ├─ 构建 messages (含 arrived_at 工具提示)     │
   │   ├─ NPC 回复 (可能调用 arrived_at 工具)        │
   │   └─ 消耗主动值 -1                             │
   │                                                │
   │ Round 2-3:                                     │
   │   ├─ 检查 walk_target_name == None ? (已确认)  │
   │   │   └─ 是 → break 结束对话                   │
   │   ├─ NPC 继续回应                              │
   │   └─ 消耗主动值 -1                             │
   │                                                │
   │ 结束时:                                         │
   │   ├─ _finalize_location_conversation() 保存记忆│
   │   └─ mem.persist() 持久化到 HJL               │
   └────────────────────────────────────────────────┘
      │
      ▼
4. 解冻 NPC: is_talking = False
      │
      ▼
5. 设置冷却锁: ban_target_uuid = "location:酒馆"
```

### 5.3 地点对话参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `max_rounds` | 3 | 地点对话最大轮次 |
| `arrived_at` 提示 | 地点问候语末尾 | "如果你已到达目的地，可以调用 arrived_at 工具确认。" |

### 5.4 地点问候语模板

```python
# social_l1.py:494-523
greetings = {
    "酒馆": "欢迎来到酒馆，{name}！这里热闹非凡，酒香四溢。",
    "广场": "你来到了村庄中心的广场，四周人来人往。",
    "市场": "市场的喧嚣声扑面而来，摊位上摆满了各种商品。",
    # ...
}
greeting += " 如果你已到达目的地，可以调用 arrived_at 工具确认。"
```

---

## 6. 冷却锁机制

### 6.1 NPC-NPC 对话冷却

| 字段 | 值 | 设置时机 | 解除条件 |
|------|-----|---------|---------|
| `ban_target_uuid` | 对方 NPC 名称 | 对话结束时 | 距离 >= `THRESHOLD_LEAVE` |

### 6.2 地点对话冷却

| 字段 | 值 | 设置时机 | 解除条件 |
|------|-----|---------|---------|
| `ban_target_uuid` | `"location:{地点名}"` | 地点对话结束时 | ⚠️ **当前无解除逻辑** |

> **注意**: 地点对话的冷却锁目前没有自动解除机制。NPC 一旦与某地点对话后，无法再次触发该地点的对话，除非手动清除 `ban_target_uuid`。

---

## 7. 地图配置参数

### 7.1 地图尺寸

| 参数 | 值 | 代码位置 |
|------|-----|---------|
| `MAP_WIDTH` | 320 (像素) | `env/map.py:16` |
| `MAP_HEIGHT` | 320 (像素) | `env/map.py:17` |
| `TILE_SIZE` | 16 (像素) | `env/map.py:15` |

### 7.2 接触阈值

| 参数 | 值 | 说明 | 代码位置 |
|------|-----|------|---------|
| `THRESHOLD_CONTACT` | 12.0 | 触发对话的距离 | `env/map.py:20` |
| `THRESHOLD_LEAVE` | 24.0 | 解除禁止的距离 | `env/map.py:21` |

---

## 8. 任务驱动移动流程

### 8.1 设计理念

NPC 行为由**自主驱动**，任务只是提示，不是强制指令：
- NPC 自己决定是否执行任务
- NPC 自己决定何时完成任务
- NPC 需要有对话机会才能收到任务提示

### 8.2 完整流程：Alice 让 Bob 去酒馆

```
=== 阶段1: Alice 下达任务 ===

Alice 与某人对话时调用:
add_task(target="Bob", hint="去酒馆等我",
         tool_hint="goto_location: location=酒馆")
    │
    ▼
[task_l1.py] 任务存入全局池:
TASK_POOL["Bob"] = [{hint, source="Alice", tool_hint, status="pending"}]

=== 阶段2: Bob 在下次对话中收到任务提示 ===

Bob 与任何人对话时 (包括地点对话):
[prompt_l2.py] format_tasks(Bob) → "去酒馆等我"
[prompt_l2.py] format_task_tools(Bob) →
    """【可用工具】
    - goto_location: 前往指定地点...
    - complete_task: 标记任务完成...
    """
    │
    ▼
Bob 的 messages 中包含:
- system: "去酒馆等我" (任务提示)
- system: 工具说明 (goto_location + complete_task)
    │
    ▼
Bob 自主决定: 调用 goto_location(location="酒馆")
    │
    ▼
[tool_l1.py] Bob.walk_mode = 'to_target'
             Bob.walk_target = (酒馆坐标)
             Bob.walk_target_name = "酒馆"

=== 阶段3: Bob 移动到酒馆 ===

每帧: drive_l1.py → move_toward_target()
Bob 向酒馆移动 (避障绕行)
    │
    ▼
到达坐标 → walk_target = None
         → walk_target_name = "酒馆" (保留)
         → _trigger_location_encounter(Bob, "酒馆")

=== 阶段4: 地点对话 ===

地点: "欢迎来到酒馆，Bob！...可以调用 arrived_at 工具确认。"
    │
    ▼
Bob 自主决定: 调用 arrived_at(location="酒馆")
    │
    ▼
[tool_l1.py] Bob.walk_mode = 'idle'
             Bob.walk_target_name = None  ← 对话检测到后结束

=== 阶段5: Bob 标记任务完成 (自主决定) ===

Bob 在后续对话中:
complete_task(hint="酒馆")  → 匹配 "去酒馆等我" 任务
    │
    ▼
任务状态: pending → completed
```

### 8.3 任务提示注入机制

| 函数 | 位置 | 作用 |
|------|------|------|
| `format_tasks()` | `prompt_l2.py:179-200` | 读取 pending 任务，生成自然语言提示 |
| `format_task_tools()` | `prompt_l2.py:203-254` | 根据 task_hint 动态注入工具说明 |

**注入时机**: NPC 的每一次对话（NPC-NPC 或 地点对话）

### 8.4 tool_hint 格式

```python
# 任务创建时
add_task(
    target="Bob",
    hint="去酒馆等我",                          # 自然语言任务描述
    tool_hint="goto_location: location=酒馆"   # 工具提示 (可选)
)

# tool_hint 格式: "工具名: 参数说明"
# 系统会提取工具名，注入对应的工具说明到 NPC 的提示词中
```

### 8.5 关键代码位置

| 功能 | 文件 | 函数 |
|------|------|------|
| 创建任务 | `tools/task_l1.py` | `_tool_add_task()` |
| 移动工具 | `tools/tool_l1.py` | `_tool_goto_location()` |
| 确认到达 | `tools/tool_l1.py` | `_tool_arrived_at()` |
| 完成任务 | `tools/task_l1.py` | `_tool_complete_task()` |
| 任务提示 | `core/prompt/prompt_l2.py` | `format_tasks()` |
| 工具注入 | `core/prompt/prompt_l2.py` | `format_task_tools()` |

---

## 9. 已知问题与待优化

### 8.1 避障问题

- **现象**: 如果所有方向都被障碍物包围，NPC 会卡在原地
- **位置**: `drive_l2.py:183-184`
- **建议**: 添加超时机制或路径规划

### 8.2 地点冷却锁

- **现象**: 地点对话后 `ban_target_uuid` 不会自动清除
- **位置**: `drive_l1.py:168`
- **建议**: 添加距离检测或时间衰减机制

### 8.3 目标被阻挡

- **现象**: 如果目标坐标本身在障碍物内，NPC 无法到达
- **位置**: `drive_l2.py:130-131`
- **建议**: 在 `goto_location` 时检查目标点是否可达