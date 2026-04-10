# 工具开发 Skill

---
description: 添加新工具时的完整流程（工具定义 + Handler实现 + 前端适配 + 提示词组装）
triggers:
  - 添加新工具
  - 修改工具定义
  - 新增对话类型
  - 配置 NPC 的 rom_tools
---

## 1. 工具添加规范

添加新工具时，**不能只添加工具定义**，必须同时完成以下配套改动：

### 1.1 必须修改的文件

| 层级 | 文件 | 改动内容 |
| :--- | :--- | :--- |
| 后端 | `tools/tool.py` | 工具定义 (`TOOL_REGISTRY`) - **唯一数据源** |
| 后端 | `tools/tool_l1.py` | Handler 实现 + `_init_handlers()` 注册 |
| 前端 | `static/src/components/Task/TaskPanel.tsx` | 参数名映射 + placeholder |

**注意**:
- 不再需要修改 `prompt_l2.py` 的 `TOOL_TEMPLATES`，工具说明从 `TOOL_REGISTRY` 动态获取
- `/api/tools` 端点已改为动态获取工具列表，无需手动维护

### 1.2 前端参数适配

`TaskPanel.tsx` 需要根据工具类型生成正确的参数名：

```tsx
// 生成 tool_hint 时，根据工具选择参数名
const paramKey = selectedTool === 'goto_location' ? 'location' : 'path';
toolHint = `${selectedTool}: ${paramKey}=${toolParam}`;

// 输入框 placeholder 也要适配
placeholder={selectedTool === 'goto_location' ? '地点名称' : '文件路径'}
```

### 1.3 工具提示词注入机制 (统一从 TOOL_REGISTRY 获取)

工具说明不再需要单独维护 `TOOL_TEMPLATES`，而是**动态从 `TOOL_REGISTRY` 生成**：

```
prompt_l2.format_task_tools() / format_npc_tools()
    ↓
从 TOOL_REGISTRY["anthropic"][tool_name] 获取
    ↓
提取 description + input_schema.properties
    ↓
生成工具说明文本，注入提示词
```

**好处**: 单一数据源，新增工具只需修改 `tools/tool.py`，提示词自动同步。

### 1.4 示例：添加 goto_location 工具

```python
# 1. tools/tool.py - 工具定义 (唯一需要添加定义的地方!)
TOOL_REGISTRY["anthropic"]["goto_location"] = {
    "description": "前往指定地点",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "地点名称如: 酒馆, 广场"},
        },
        "required": ["location"],
    },
    "handler": None,
    "enabled": True,
}

# 2. tools/tool_l1.py - Handler 实现
def _tool_goto_location(input_obj: dict, npc, context) -> str:
    location_name = input_obj.get("location", "")
    from env import map as map_module
    coords = map_module.get_location_coords(location_name)
    if coords:
        npc.walk_mode = 'to_target'
        npc.walk_target = coords
        return f"开始前往 {location_name}"
    return f"错误: 未找到地点 '{location_name}'"

# 3. tools/tool_l1.py - 注册 Handler (在 _init_handlers 中)
tool_module.TOOL_REGISTRY["anthropic"]["goto_location"]["handler"] = _tool_goto_location
```

```tsx
// 4. static/src/components/Task/TaskPanel.tsx - 前端适配

// 生成 tool_hint 时，根据工具选择参数名
const paramKey = selectedTool === 'goto_location' ? 'location' : 'path';
toolHint = `${selectedTool}: ${paramKey}=${toolParam}`;

// 输入框 placeholder 适配
<Input
  placeholder={selectedTool === 'goto_location' ? '地点名称' : '文件路径'}
  ...
/>
```

### 1.5 tool_hint 格式规范

```python
# add_task 调用示例
add_task(
    target="Bob",
    hint="去酒馆等我",
    tool_hint="goto_location: location=酒馆"  # 格式: "工具名: 参数说明"
)
```

### 1.6 带外部依赖的工具 (如 QQ 通知)

某些工具需要外部配置或依赖模块，添加流程略有不同：

| 步骤 | 文件 | 改动 |
|------|------|------|
| 1 | `tools/xxx.py` | 总控层 - 配置加载、接口暴露 |
| 2 | `tools/xxx_l1.py` | 业务层 - 核心逻辑 |
| 3 | `tools/xxx_l2.py` | 原子层 - 纯计算/HTTP请求 |
| 4 | `config/xxx.json` | 配置文件 (敏感信息) |
| 5 | `tools/tool.py` | 工具定义 (`TOOL_REGISTRY`) |
| 6 | `tools/tool_l1.py` | Handler 实现 + 注册 |

**示例：`send_qq_notify` 工具**

```
tools/
├── qq_bot.py           # 总控层 - 从 config/qq_bot.json 加载配置
├── qq_bot_l1.py        # 业务层 - Token 缓存、消息发送
└── qq_bot_l2.py        # 原子层 - HTTP POST 请求

config/
└── qq_bot.json         # 配置 (app_id, client_secret, admin_openid)
```

**注意**：
- 这类工具只需要 **`rom_tools` 配置**，不需要 `main.py` 的 `TASK_TOOLS`
- 配置文件放在 `config/` 目录，敏感信息不要提交到 git

---

## 2. NPC 工具调用完整流程 (rom_tools 机制)

前端配置 NPC 的 `rom_tools` 后，系统如何让 NPC 真正调用工具：

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

**关键点**：

1. **严格匹配**: 前端配置什么工具，就只传什么工具，不多不少
2. **双重注入**:
   - `npc_tools_text` → 提示词，让 LLM 知道有哪些工具可用
   - `npc_tools` → API tools 参数，让 LLM 返回结构化的 tool_use
3. **分层职责**:
   - `tools/tool.py`: 工具定义，不关心 NPC 结构
   - `prompt_l2.py`: 读取 NPC 配置，生成上下文
   - `social_l1.py`: 从 context 获取工具定义，调用 LLM

---

## 3. 提示词组装规范 (模板 vs 手动)

⚠️ **新增对话类型时必须阅读此节！**

### 3.1 两种组装方式

| 方式 | 使用场景 | 入口函数 | 任务提示注入 |
|------|----------|----------|-------------|
| **模板渲染** | NPC 之间对话 | `prompt_l1.assemble()` | ✅ 自动 (模板中 `{tasks_text}`) |
| **手动组装** | 定时器对话、地点对话 | `_build_xxx_messages()` | ⚠️ **需手动注入** |

### 3.2 上下文变量清单 (build_context 返回)

当手动组装 messages 时，必须参考以下变量决定需要注入哪些内容：

| 变量名 | 用途 | 示例内容 |
|--------|------|----------|
| `time_str` + `period` | 当前时间 | `08:30 (早晨)` |
| `persona` | 人设描述 | `你是 Alex，程序员...` |
| `memory_text` | 历史记忆 | 格式化后的记忆条目 |
| `tasks_text` | **待办任务描述** | `去酒馆等我` |
| `task_tools_text` | **任务工具提示** | `goto_location: location=酒馆` |
| `npc_tools_text` | NPC 配置的工具提示 | `read_file: 读取文件...` |
| `lore_text` | 世界观 | 故事背景 |
| `relation_desc` | 关系描述 | `你们是同事` |

### 3.3 手动组装的完整示例

```python
def _build_timer_messages(npc, description: str):
    """定时器对话 - 手动组装示例"""
    from core.prompt import prompt, prompt_l2

    messages = []

    # 1. 当前时间
    time_info = world_time.get_time_info()
    time_str = f"当前时间: {time_info['time_str']} ({time_info['period']})"
    messages.append({"role": "system", "content": time_str})

    # 2. 人设
    persona = npc.memory.get('rom_personality', '')
    if persona:
        messages.append({"role": "system", "content": persona})

    # 3. 历史记忆
    memory_text = prompt.format_memory_for_timer(npc)
    if memory_text:
        messages.append({"role": "system", "content": f"[你的记忆]:\n{memory_text}"})

    # 4. ⚠️ 待办任务描述 (必须注入！)
    tasks_text = prompt_l2.format_tasks(npc, None)
    if tasks_text:
        messages.append({"role": "system", "content": f"[你的待办任务]:\n{tasks_text}"})

    # 5. ⚠️ 任务工具提示 (必须注入！)
    task_tools_text = prompt_l2.format_task_tools(npc)
    if task_tools_text:
        messages.append({"role": "system", "content": task_tools_text})

    # 6. NPC 配置工具提示
    npc_tools_text = prompt_l2.format_npc_tools(npc)
    if npc_tools_text:
        messages.append({"role": "system", "content": npc_tools_text})

    # 7. 触发内容
    messages.append({"role": "user", "content": f"[定时提醒] {description}"})

    # 8. 生成 context (供 API 层使用)
    context = prompt_l2.build_context(npc, None, {})

    return messages, context
```

### 3.4 新增对话类型的检查清单

当添加新的对话类型（如环境触发、事件触发等）时，**必须确认**：

- [ ] 是否需要 `tasks_text`（任务描述）？
- [ ] 是否需要 `task_tools_text`（任务工具提示）？
- [ ] 是否需要 `npc_tools_text`（NPC 配置工具）？
- [ ] 是否需要 `memory_text`（历史记忆）？
- [ ] 是否调用 `build_context()` 生成完整的 context？

**参考对比**：

| 对话类型 | tasks_text | task_tools_text | npc_tools_text |
|----------|:----------:|:---------------:|:--------------:|
| NPC 之间对话 | ✅ (模板) | ✅ (模板) | ✅ (模板) |
| 定时器对话 | ✅ | ✅ | ✅ |
| 地点对话 | ✅ | ✅ | ✅ |
| 新对话类型 | ❓ | ❓ | ❓ |
