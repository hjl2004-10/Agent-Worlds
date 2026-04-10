# 对话流程文档

本文档描述 AI_夸父 系统中的对话机制，包括 NPC 对话、地点对话和工具调用的完整流程。

---

## 1. NPC 对话流程

### 1.1 触发条件

当两个 NPC 距离小于 `CONTACT_THRESHOLD`（默认 2.0）时触发对话。

```
┌─────────────────────────────────────────┐
│         main.py 主循环                    │
│                                         │
│  while True:                            │
│      drive.update_all(npcs)  # 移动     │
│      social.run(npcs)        # 社交     │
│          ↓                              │
│      检测 NPC 间距离 < 2.0               │
│          ↓                              │
│      run_conversation(npc_a, npc_b)     │
└─────────────────────────────────────────┘
```

### 1.2 对话轮次机制

```
┌─────────────────────────────────────────────────────────────────┐
│                    run_conversation(npc_a, npc_b)                │
│                                                                 │
│  1. 清空双方的 ram_buffer，开始新对话                             │
│  2. 循环 (最多 15 轮):                                          │
│     a. 判定发言者 (主动值高的先说话)                              │
│     b. 检查主动值是否枯竭 (< 0)                                  │
│     c. 获取回复:                                                │
│        - 玩家: wait_for_player_input()                          │
│        - AI: build_messages() → LLM                             │
│     d. 更新双方的 ram_buffer                                     │
│     e. 消耗发言者主动值 (-1)                                     │
│  3. 对话结束，持久化到 HJL 文件                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 消息构建流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    build_messages(speaker, listener)             │
│                                                                 │
│  检查 speaker.memory['rom_prompt']:                             │
│  ├── 有配置 → prompt_module.build(speaker, listener)            │
│  │              ↓                                               │
│  │         prompt_l1.assemble()                                 │
│  │              ↓                                               │
│  │         prompt_l2.build_context() 生成 context               │
│  │              ↓                                               │
│  │         返回 (messages, context)                             │
│  │                                                              │
│  └── 无配置 → _build_messages_legacy() + 空 context             │
│                                                                 │
│  返回: (messages, context)                                       │
│  - messages: LLM 消息数组                                        │
│  - context: 包含 npc_tools 等上下文变量                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 地点对话流程

### 2.1 触发条件

当 NPC 使用 `goto_location` 工具到达目的地时触发。

```
┌─────────────────────────────────────────────────────────────────┐
│                    drive_l1.py 移动检测                          │
│                                                                 │
│  if npc.walk_mode == 'to_target':                               │
│      dist = distance(npc, npc.walk_target)                      │
│      if dist < 1.0:  # 到达                                     │
│          run_location_conversation(npc, npc.walk_target_name)   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 地点对话流程

```
┌─────────────────────────────────────────────────────────────────┐
│              run_location_conversation(npc, location_name)       │
│                                                                 │
│  1. 清空 NPC 的 ram_buffer                                       │
│  2. 循环 (最多 3 轮):                                            │
│                                                                 │
│     Round 1: 地点主动发起                                        │
│     ┌───────────────────────────────────────────────────────┐   │
│     │ [酒馆]: "欢迎来到酒馆，Bob！这里热闹非凡...             │   │
│     │         如果你已到达目的地，可以调用 arrived_at 工具确认"│   │
│     └───────────────────────────────────────────────────────┘   │
│                          ↓                                      │
│     NPC 回复 (带工具调用检测)                                    │
│                          ↓                                      │
│     存入 ram_buffer, 消耗主动值                                  │
│                                                                 │
│     Round 2-3: NPC 可继续回应或结束                              │
│     ┌───────────────────────────────────────────────────────┐   │
│     │ 检查 walk_target_name:                                 │   │
│     │ ├── != None: 还没确认到达，继续对话                    │   │
│     │ └── == None: 已调用 arrived_at，结束对话               │   │
│     └───────────────────────────────────────────────────────┘   │
│                                                                 │
│  3. 对话结束，保存记忆到 HJL                                     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 地点消息构建

```
┌─────────────────────────────────────────────────────────────────┐
│           _build_location_messages(npc, location_name)           │
│                                                                 │
│  1. 当前时间 (system)                                            │
│  2. 人设描述 (system)                                            │
│  3. 历史记忆 (筛选与地点相关的)                                   │
│  4. 工具提示 (非 Anthropic 协议时注入 arrived_at 说明)           │
│  5. 当前对话流 (ram_buffer)                                      │
│  6. 初始提示 (如果没有对话流)                                    │
│  7. 调用 prompt_l2.build_context(npc) 生成 context               │
│                                                                 │
│  返回: (messages, context)                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 工具调用流程 (rom_tools 机制)

### 3.1 完整流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            前端配置 (NPC 编辑器)                              │
│                                                                             │
│   rom_tools: ["read_file", "write_file"]                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
                                    ↓ 持久化到 HJL
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         data/individuals/david.hjl                          │
│                                                                             │
│   {                                                                         │
│     "attributes": {                                                         │
│       "rom_tools": ["read_file", "write_file"]                              │
│     }                                                                       │
│   }                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
                                    ↓ 系统启动时加载
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      npc.memory['rom_tools'] (内存)                         │
│                                                                             │
│   npc.memory['rom_tools'] = ["read_file", "write_file"]                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
                                    ↓ 对话开始
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    prompt_l2.build_context() 生成上下文                      │
│                                                                             │
│   1. get_npc_tool_definitions(speaker)                                      │
│      → 调用 tools/tool.py 的 get_anthropic_tool_definitions(speaker)        │
│      → 只返回 rom_tools 里配置的工具定义 (API 格式)                           │
│                                                                             │
│   2. format_npc_tools(speaker)                                              │
│      → 生成工具的文本描述 (用于提示词)                                        │
│                                                                             │
│   3. 返回 context = {                                                       │
│        'npc_tools': [...],        # API tools 参数 (结构化)                 │
│        'npc_tools_text': '...',   # 提示词中的工具说明 (文本)                │
│      }                                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
                                    ↓ prompt_l1.assemble()
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                     返回 (messages, context)                                 │
│                                                                             │
│   messages = [                                                              │
│     {"role": "system", "content": "【你的能力工具】\n- read_file: ..."},     │
│     ...                                                                     │
│   ]                                                                         │
│   context = {'npc_tools': [...], ...}                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
                                    ↓ social_l1 调用 LLM
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM API 请求                                         │
│                                                                             │
│   {                                                                         │
│     "model": "claude-3-sonnet",                                             │
│     "messages": [...],                    # 包含 npc_tools_text (提示词)    │
│     "tools": context['npc_tools']         # 只有 read_file, write_file      │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
                                    ↓ LLM 返回 tool_use
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         工具执行 & 返回结果                                   │
│                                                                             │
│   1. 解析 tool_use: {"type": "tool_use", "name": "read_file", ...}          │
│   2. 执行 handler: tool_l1.py 中的 _tool_read_file()                        │
│   3. 返回 tool_result 给 LLM                                                │
│   4. LLM 生成最终回复                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 关键点

| 特性 | 说明 |
|------|------|
| **严格匹配** | 前端配置什么工具，就只传什么工具，不多不少 |
| **双重注入** | `npc_tools_text` → 提示词，`npc_tools` → API tools 参数 |
| **分层职责** | `tools/tool.py`: 工具定义；`prompt_l2.py`: 读取配置；`social_l1.py`: 调用 LLM |

### 3.3 工具调用检测条件

```python
def _should_use_tools(npc) -> bool:
    """
    检查 NPC 是否应该使用 Anthropic 工具

    条件:
    1. 使用 claude 协议的渠道
    2. 有待办任务需要工具 (task.tool_hint 存在)
    """
    # 检查渠道是否是 claude 协议
    if provider != "claude":
        return False

    # 检查是否有待办任务需要工具
    pending_tasks = get_pending_tasks_for(npc.name)
    for task in pending_tasks:
        if task.get('tool_hint'):
            return True

    return False
```

### 3.4 工具合并逻辑

```python
def _chat_with_tool_loop(messages, context, speaker, listener, channel, model):
    # 获取任务相关的工具定义 (来自 task.tool_hint)
    task_tools = get_task_tool_definitions(speaker)

    # 获取 NPC 配置的工具定义 (来自 rom_tools)
    npc_tools = context.get('npc_tools', [])

    # 合并工具列表 (去重)
    tools = []
    tool_names = set()
    for t in task_tools + npc_tools:
        name = t.get("name")
        if name and name not in tool_names:
            tool_names.add(name)
            tools.append(t)
```

---

## 4. 记忆系统 (RAM vs 持久化)

### 4.1 两种存储

| 类型 | 存储位置 | 生命周期 | API |
|------|----------|----------|-----|
| **RAM Buffer** | `npc.memory['ram_buffer']` | 对话期间瞬时存在 | `/api/conversation/ram/{npc_name}` |
| **历史记忆** | `data/individuals/{name}.hjl` | 永久持久化 | `/api/memory/{npc_name}` |

### 4.2 数据流向

```
对话开始
    ↓
NPC 说话 → 写入 ram_buffer (内存)
    ↓
对话继续 → ram_buffer 累积
    ↓
对话结束 → ram_buffer 持久化到 HJL 文件
    ↓
ram_buffer 清空，等待下次对话
```

---

## 5. 任务驱动对话示例

### 5.1 完整任务链

```
玩家给 Bob 任务: "去酒馆拿封信给我"
    ↓
前端调用: add_task(target="Bob", hint="去酒馆拿封信", tool_hint="goto_location: location=酒馆")
    ↓
Bob 收到任务，开始移动
    ↓
Bob 到达酒馆 → 触发地点对话
    ↓
Bob 可用工具:
  - arrived_at (来自 task_tools，确认到达)
  - read_file (来自 rom_tools，读取信件)
  - write_file (来自 rom_tools，写回信)
    ↓
Bob 调用 arrived_at("酒馆") → 任务完成
```

### 5.2 工具提示词注入

```
当 NPC 有待办任务时，提示词会注入:

【当前任务】
- 去酒馆拿封信
- 可用工具: goto_location (前往指定地点)

【你的能力工具】
- read_file: 读取文件内容
- write_file: 写入文件内容
```

---

## 6. 相关文件

| 文件 | 职责 |
|------|------|
| `core/social/social_l1.py` | 对话流程控制、消息构建 |
| `core/social/social_l2.py` | 原子操作 (判定接触、比较主动值) |
| `core/prompt/prompt.py` | 提示词总控 |
| `core/prompt/prompt_l1.py` | 提示词组装 |
| `core/prompt/prompt_l2.py` | 上下文生成、工具定义 |
| `tools/tool.py` | 工具定义注册 |
| `tools/tool_l1.py` | 工具执行 Handler |
