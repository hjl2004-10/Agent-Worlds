# NPC Skill & MCP 技术文档

> 本文档面向外部开发者，讲解夸父系统中 NPC 如何通过 **Skill（技能）** 和 **MCP（Model Context Protocol）** 获得可扩展的工具调用能力。

---

## 一、核心概念总览

NPC 本身只是一个"人格容器"——它有名字、性格、记忆，但**没有任何能力**。

**Skill** 赋予 NPC 能力。一个 Skill = 一组工具 + 一段提示词。

**MCP** 让 NPC 连接外部服务器，动态获取远程工具。

```
┌─────────────────────────────────────────────────┐
│                   NPC (Alice)                   │
│                                                 │
│  人格 ← HJL 文件定义                            │
│  记忆 ← RAM Buffer + HJL 持久化                 │
│                                                 │
│  ┌─────────────┐  ┌──────────────────────────┐  │
│  │   Skills     │  │      MCP Servers         │  │
│  │             │  │                          │  │
│  │ programmer  │  │  weather-server  ──────┐ │  │
│  │  → read_file│  │  → get_forecast       │ │  │
│  │  → write_file│  │  → get_current       │ │  │
│  │  → edit_text│  │                       │ │  │
│  │             │  │  search-server  ─────┐│ │  │
│  │ navigator   │  │  → web_search       ││ │  │
│  │  → goto     │  │  → lookup_place     ││ │  │
│  └─────────────┘  └──────────────────────┘│  │
│         │                    │              │  │
│         ▼                    ▼              │  │
│  ┌─────────────────────────────────────┐   │  │
│  │         合并的工具列表               │   │  │
│  │  [read_file, write_file, edit_text, │   │  │
│  │   goto, mcp__weather__get_forecast, │   │  │
│  │   mcp__search__web_search, ...]     │   │  │
│  └─────────────────────────────────────┘   │  │
│                    │                        │  │
│                    ▼                        │  │
│             LLM 对话时按需调用              │  │
└─────────────────────────────────────────────┘
```

---

## 二、Skill 系统

### 2.1 什么是 Skill？

Skill 是一个**可插拔的能力模块**，包含：

| 组成部分 | 文件 | 作用 |
|---------|------|------|
| 元数据 | `skill.hjl` | 声明工具列表、描述、MCP 依赖 |
| 提示词 | `prompt.md` | 教 NPC 如何使用这些工具 |

### 2.2 Skill 目录结构

```
data/skills/
├── programmer/          # "程序员"技能
│   ├── skill.hjl        # 元数据：我有哪些工具
│   └── prompt.md        # 提示词：怎么用这些工具
│
├── navigator/           # "导航者"技能
│   ├── skill.hjl
│   └── prompt.md
│
└── analyst/             # "分析师"技能
    ├── skill.hjl
    └── prompt.md
```

### 2.3 Skill 定义格式 (`skill.hjl`)

```json
{
  "name": "programmer",
  "description": "文件读写编辑能力",
  "tools": ["@file", "delete_file"],
  "prompt_file": "prompt.md",
  "mcp_server": null
}
```

**关键字段：**

- **`tools`**：工具列表，支持 `@` 前缀引用**工具组**
- **`mcp_server`**：可选，该技能依赖的 MCP 服务器配置
- **`prompt_file`**：提示词文件，教 LLM 如何正确使用工具

### 2.4 工具组展开机制

`@file` 不是一个真实工具，而是一个**工具组别名**：

```
@file  ──展开──▶  [read_file, write_file, edit_text]
```

工具组定义在 `config/tool_groups.json`：

```json
{
  "groups": {
    "@file": {
      "description": "文件操作工具集",
      "tools": ["read_file", "write_file", "edit_text"]
    }
  }
}
```

**好处**：多个 Skill 都用 `@file`，底层工具改了只需改一处。

### 2.5 NPC 装备 Skill

在 NPC 的 HJL 配置文件中声明：

```json
{
  "header": { "name": "Alice", "uuid": "npc_001" },
  "attributes": {
    "skills": ["programmer", "navigator"],
    "tools": ["ask_human"],
    "tools_prompt": "遇到困难时可以询问人类。"
  }
}
```

- **`skills`**：引用 `data/skills/` 下的技能
- **`tools`**：额外的独立工具（不属于任何 Skill）
- **`tools_prompt`**：额外的工具提示词

### 2.6 Skill 加载流程图

```
NPC HJL 文件
    │
    │  attributes.skills = ["programmer", "navigator"]
    │  attributes.tools  = ["ask_human"]
    │
    ▼
┌──────────────────────────────────────┐
│    skill.resolve_skills_for_npc()    │
│              (总控层)                 │
└──────────────┬───────────────────────┘
               │
    ┌──────────┴──────────┐
    ▼                     ▼
┌────────────┐    ┌────────────┐
│ load_skill │    │ load_skill │
│"programmer"│    │"navigator" │
│   (L1)     │    │   (L1)     │
└─────┬──────┘    └─────┬──────┘
      │                 │
      │  tools:         │  tools:
      │  [@file,        │  [goto_location]
      │   delete_file]  │
      │                 │  prompt:
      │  prompt:        │  "导航相关..."
      │  "编程相关..."   │
      │                 │
      ▼                 ▼
┌──────────────────────────────────────┐
│      skill_l2.merge_tool_lists()     │
│                                      │
│  展开 @file → [read_file,            │
│                write_file,           │
│                edit_text]            │
│                                      │
│  合并 + 去重:                         │
│  [read_file, write_file, edit_text,  │
│   delete_file, goto_location,        │
│   ask_human]          ← 额外工具追加  │
│                                      │
│  拼接 prompt:                         │
│  "编程相关...\n---\n导航相关...\n      │
│   ---\n遇到困难时可以询问人类。"        │
└──────────────────────────────────────┘
               │
               ▼
        存入 NPC 内存
        agent.memory['rom_tools']        = [工具名列表]
        agent.memory['rom_tools_prompt'] = "合并后的提示词"
```

---

## 三、MCP 系统

### 3.1 什么是 MCP？

**MCP (Model Context Protocol)** 是一个开放协议，让 AI 模型能够连接外部工具服务器。

在夸父系统中，MCP 让 NPC 能够调用**远程服务**——天气查询、网页搜索、数据库操作等，而无需在本地实现这些工具。

```
┌──────────┐     MCP 协议      ┌──────────────┐
│          │  ◀────────────▶  │              │
│   NPC    │    连接 + 调用    │  MCP Server  │
│ (客户端)  │                  │  (工具提供方)  │
│          │                  │              │
└──────────┘                  └──────────────┘

MCP 服务器可以是：
  • 本地进程 (stdio)
  • 远程 HTTP 服务 (SSE)
  • 任何实现了 MCP 协议的服务
```

### 3.2 MCP 三层架构

```
┌─────────────────────────────────────────────┐
│  mcp_client.py (总控层 L0)                   │
│                                             │
│  • 管理异步事件循环（后台线程）                 │
│  • 缓存服务器连接和工具定义                    │
│  • 对外暴露同步 API                          │
│                                             │
│  connect_npc_servers()  ←── 公开接口          │
│  call_tool()            ←── 公开接口          │
├─────────────────────────────────────────────┤
│  mcp_client_l1.py (业务层 L1)                │
│                                             │
│  • 建立 MCP 连接（SSE/stdio）                 │
│  • 发现工具列表 (list_tools)                  │
│  • 执行工具调用 (call_tool)                   │
│  • 全部是 async 函数                         │
├─────────────────────────────────────────────┤
│  mcp_client_l2.py (原子层 L2)                │
│                                             │
│  • MCP 工具定义 → Anthropic 格式转换          │
│  • 工具名解析：mcp__server__tool             │
│  • 结果格式化                                │
└─────────────────────────────────────────────┘
```

### 3.3 MCP 工具命名规则

MCP 工具使用双下划线命名空间：

```
mcp__{服务器名}__{工具名}

示例:
  mcp__weather__get_forecast     ← weather 服务器的 get_forecast 工具
  mcp__search__web_search        ← search 服务器的 web_search 工具
  mcp__database__run_query       ← database 服务器的 run_query 工具
```

**为什么这样命名？**
- 避免与本地工具冲突
- 执行时可以快速路由到正确的 MCP 服务器
- LLM 能从名字理解工具来源

### 3.4 MCP 连接流程

```
系统启动 → 加载 NPC
               │
               ▼
┌──────────────────────────────────────────┐
│     mcp_client.init()                    │
│                                          │
│  1. 创建 asyncio 事件循环                 │
│  2. 在后台线程启动事件循环                 │
│     (因为主程序是同步的，                  │
│      但 MCP 协议是异步的)                 │
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│  connect_npc_servers(npc_name, servers)  │
│                                          │
│  对每个 MCP 服务器:                       │
│    ┌─────────────────────────────────┐   │
│    │  connect_and_list_tools()       │   │
│    │                                 │   │
│    │  1. 建立 MCP 连接 (SSE/stdio)   │   │
│    │  2. 调用 list_tools()           │   │
│    │  3. 获取工具列表                 │   │
│    │  4. 转换为 Anthropic 格式        │   │
│    └─────────────────────────────────┘   │
│                                          │
│  返回: [                                 │
│    {name: "mcp__weather__get_forecast",  │
│     description: "[MCP:weather] ...",    │
│     input_schema: {...}},                │
│    ...                                   │
│  ]                                       │
└────────────────┬─────────────────────────┘
                 │
                 ▼
        存入 NPC 内存
        agent.memory['mcp_tool_defs'] = [工具定义列表]
```

### 3.5 同步-异步桥接

MCP 协议基于异步 I/O，但夸父主循环是同步的。解决方案：

```
┌──────────────────┐       ┌─────────────────────┐
│   主线程 (同步)    │       │  后台线程 (异步)      │
│                  │       │                     │
│  social_l1.py    │       │  asyncio 事件循环     │
│  调用 call_tool()│       │                     │
│       │          │       │                     │
│       ▼          │       │                     │
│  run_coroutine_  │──────▶│  执行 MCP 异步调用    │
│  threadsafe()    │       │       │              │
│       │          │       │       ▼              │
│  等待结果 ◀───────│───────│  返回结果             │
│       │          │       │                     │
│       ▼          │       │                     │
│  继续处理         │       │                     │
└──────────────────┘       └─────────────────────┘
```

---

## 四、完整调用流程

### 4.1 端到端流程：从对话到工具执行

```
用户对 NPC 说话
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  social_l1._chat_with_tool_loop()                      │
│                                                        │
│  Step 1: 收集所有可用工具                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  本地工具 (from rom_tools)                        │  │
│  │  ├── read_file      ← Skill "programmer"        │  │
│  │  ├── write_file     ← Skill "programmer"        │  │
│  │  ├── edit_text      ← Skill "programmer"        │  │
│  │  └── goto_location  ← Skill "navigator"         │  │
│  │                                                  │  │
│  │  MCP工具 (from mcp_tool_defs)                     │  │
│  │  ├── mcp__weather__get_forecast  ← MCP Server   │  │
│  │  └── mcp__search__web_search    ← MCP Server   │  │
│  │                                                  │  │
│  │  任务工具 (from pending tasks)                     │  │
│  │  └── complete_task              ← 动态注入       │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  Step 2: 构建 Prompt                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  [系统] 时间: 09:30 早上                          │  │
│  │  [系统] 人设: 你是一个程序员...                     │  │
│  │  [系统] 记忆: 昨天和 Bob 讨论过...                  │  │
│  │  [系统] 【你的技能】                               │  │
│  │         read_file: 读取文件内容                    │  │
│  │         write_file: 写入文件                      │  │
│  │         mcp__weather__get_forecast: 查询天气       │  │
│  │  [用户] 帮我看看 config.json 的内容                 │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  Step 3: 调用 LLM                                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  llm.chat_with_tools(                            │  │
│  │    messages = [...],                             │  │
│  │    tools = [所有工具定义],      ← Anthropic 格式   │  │
│  │    tool_executor = callback,  ← 执行回调          │  │
│  │    max_tool_loops = 10        ← 最多连续调用10次   │  │
│  │  )                                               │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  Step 4: LLM 决定使用工具                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  LLM 返回:                                       │  │
│  │  {                                               │  │
│  │    "type": "tool_use",                           │  │
│  │    "name": "read_file",                          │  │
│  │    "input": {"path": "config.json"}              │  │
│  │  }                                               │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  Step 5: 路由 & 执行                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  tool_executor(tool_uses):                       │  │
│  │                                                  │  │
│  │    tool_name = "read_file"                       │  │
│  │                                                  │  │
│  │    if tool_name.startswith("mcp__"):             │  │
│  │        → MCP 路由 (见下方)                        │  │
│  │    else:                                         │  │
│  │        → 本地工具注册表查找                        │  │
│  │        → TOOL_REGISTRY["anthropic"]["read_file"] │  │
│  │        → handler(input, npc, context)            │  │
│  │        → 返回文件内容                             │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  Step 6: 结果返回 LLM，继续对话                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  LLM 收到工具结果，生成最终回复:                    │  │
│  │  "config.json 的内容是..."                        │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### 4.2 MCP 工具路由细节

当 LLM 返回的工具名以 `mcp__` 开头时：

```
tool_name = "mcp__weather__get_forecast"
                │          │
                ▼          ▼
          server_name  actual_tool_name
          = "weather"  = "get_forecast"

    ┌─────────────────────────────────────┐
    │  mcp_client_l2.parse_mcp_tool_name()│
    │                                     │
    │  "mcp__weather__get_forecast"       │
    │    → ("weather", "get_forecast")    │
    └─────────────────┬───────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────┐
    │  mcp_client.call_tool()             │
    │                                     │
    │  1. 从缓存查找 weather 服务器连接    │
    │  2. 异步调用 get_forecast(input)     │
    │  3. 等待结果                         │
    │  4. 格式化为字符串返回               │
    └─────────────────────────────────────┘
```

### 4.3 多轮工具调用（Tool Loop）

NPC 可以**连续多次**使用工具，最多 10 轮：

```
         ┌───────────────────────────┐
         │       LLM 调用            │
         └─────────┬─────────────────┘
                   │
            ┌──────▼──────┐
            │ 返回内容类型？│
            └──────┬──────┘
                   │
          ┌────────┴────────┐
          │                 │
    ┌─────▼─────┐    ┌─────▼─────┐
    │  纯文本    │    │ tool_use  │
    │  (结束)    │    │ (工具调用) │
    └───────────┘    └─────┬─────┘
                           │
                    ┌──────▼──────┐
                    │  执行工具    │
                    │  获取结果    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ 结果放入消息  │
                    │ 再次调用 LLM │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  循环次数    │
                    │  < 10 ?     │
                    └──────┬──────┘
                      是 │    │ 否
                         │    │
                  ┌──────▼┐  ┌▼──────────┐
                  │回到顶部│  │ 强制结束   │
                  │再判断  │  │ 返回最后结果│
                  └───────┘  └───────────┘
```

---

## 五、三层架构对照表

整个系统严格遵循**总控-业务-原子**三层架构：

```
┌─────────────────────────────────────────────────────────────┐
│                        总控层 (L0)                           │
│                  配置持有 + 接口定义                          │
│                                                             │
│  skill.py          mcp_client.py         tool.py            │
│  ┌────────────┐    ┌────────────────┐    ┌───────────────┐  │
│  │ SKILLS_DIR │    │ _loop (事件循环)│    │ TOOL_REGISTRY │  │
│  │ _cache     │    │ _thread        │    │               │  │
│  │            │    │ _server_configs│    │               │  │
│  │ resolve_   │    │                │    │ get_tool_     │  │
│  │ skills_for_│    │ connect_npc_   │    │ definitions() │  │
│  │ npc()      │    │ servers()      │    │               │  │
│  └────────────┘    │ call_tool()    │    └───────────────┘  │
│                    └────────────────┘                        │
├─────────────────────────────────────────────────────────────┤
│                        业务层 (L1)                           │
│                  个体作用域 + 流程组装                        │
│                                                             │
│  skill_l1.py       mcp_client_l1.py      tool_l1.py         │
│  ┌────────────┐    ┌────────────────┐    ┌───────────────┐  │
│  │ load_skill │    │ connect_and_   │    │ _tool_read_   │  │
│  │ _data()    │    │ list_tools()   │    │ file()        │  │
│  │            │    │                │    │               │  │
│  │ resolve()  │    │ call_tool()    │    │ _tool_write_  │  │
│  │            │    │   (async)      │    │ file()        │  │
│  └────────────┘    └────────────────┘    │               │  │
│                                          │ _tool_goto()  │  │
│                                          │ ...30+ 工具   │  │
│                                          └───────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                        原子层 (L2)                           │
│                  纯函数 + 无状态                             │
│                                                             │
│  skill_l2.py       mcp_client_l2.py      tool_l2.py         │
│  ┌────────────┐    ┌────────────────┐    ┌───────────────┐  │
│  │ merge_tool │    │ mcp_tool_to_  │    │ match_        │  │
│  │ _lists()   │    │ anthropic()    │    │ trigger()     │  │
│  │            │    │                │    │               │  │
│  │ concat_    │    │ parse_mcp_    │    │               │  │
│  │ prompts()  │    │ tool_name()    │    │               │  │
│  └────────────┘    │                │    └───────────────┘  │
│                    │ mcp_result_   │                        │
│                    │ to_string()    │                        │
│                    └────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、实战示例

### 6.1 给 NPC 添加一个新 Skill

**场景**：让 NPC "Bob" 拥有邮件发送能力。

**Step 1** — 创建 Skill 目录：

```
data/skills/mailer/
├── skill.hjl
└── prompt.md
```

**Step 2** — 定义 `skill.hjl`：

```json
{
  "name": "mailer",
  "description": "邮件发送能力",
  "tools": ["send_mail", "send_html_mail"],
  "prompt_file": "prompt.md",
  "mcp_server": null
}
```

**Step 3** — 编写 `prompt.md`：

```markdown
## 邮件能力

你可以发送邮件。使用规则：
- 发送前确认收件人和内容
- 重要邮件使用 send_html_mail 以获得更好的排版
- 普通通知使用 send_mail 即可
```

**Step 4** — 在 Bob 的 HJL 中装备：

```json
{
  "attributes": {
    "skills": ["mailer"]
  }
}
```

**完成！** Bob 重新加载后就拥有了邮件能力。

### 6.2 给 NPC 连接 MCP 服务器

**场景**：让 NPC "Alice" 能查询天气。

**方式 A** — 在 Skill 中声明 MCP：

```json
// data/skills/weatherman/skill.hjl
{
  "name": "weatherman",
  "description": "天气查询能力",
  "tools": [],
  "prompt_file": "prompt.md",
  "mcp_server": {
    "url": "http://weather-mcp:8000/sse",
    "name": "weather"
  }
}
```

**方式 B** — 在 NPC HJL 中直接配置：

```json
{
  "attributes": {
    "mcp_servers": [
      {"url": "http://weather-mcp:8000/sse", "name": "weather"}
    ]
  }
}
```

**效果**：系统启动时自动连接 MCP 服务器，发现工具，NPC 对话中即可调用。

---

## 七、关键源码索引

| 文件 | 职责 | 核心函数 |
|------|------|---------|
| `tools/skill.py` | Skill 总控 | `resolve_skills_for_npc()` |
| `tools/skill_l1.py` | Skill 加载 | `load_skill_data()`, `resolve()` |
| `tools/skill_l2.py` | 合并逻辑 | `merge_tool_lists()`, `concat_prompts()` |
| `tools/mcp_client.py` | MCP 总控 | `connect_npc_servers()`, `call_tool()` |
| `tools/mcp_client_l1.py` | MCP 连接 | `connect_and_list_tools()` (async) |
| `tools/mcp_client_l2.py` | 格式转换 | `mcp_tool_to_anthropic()`, `parse_mcp_tool_name()` |
| `tools/tool.py` | 工具注册表 | `TOOL_REGISTRY`, `expand_tool_groups()` |
| `tools/tool_l1.py` | 工具处理器 | `_tool_read_file()` 等 30+ handler |
| `tools/loader_l1.py` | NPC 加载 | `load_npc_from_file()` |
| `core/prompt/prompt_l2.py` | Prompt 构建 | `build_context()`, `format_npc_tools()` |
| `core/social/social_l1.py` | 对话主循环 | `_chat_with_tool_loop()` |

---

## 八、设计哲学

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   NPC 是"人"，Skill 是"职业"，MCP 是"外包"       │
│                                                 │
│   • NPC 不知道工具怎么实现                        │
│     它只知道"我能做什么"（Skill 告诉它的）         │
│                                                 │
│   • Skill 是可组合的                             │
│     一个 NPC 可以同时是 programmer + navigator   │
│                                                 │
│   • MCP 是透明的                                 │
│     远程工具和本地工具对 NPC 来说没有区别           │
│     都是"调用一个函数，拿到结果"                   │
│                                                 │
│   • 三层架构保证可维护性                          │
│     总控管配置，业务管流程，原子管计算              │
│                                                 │
└─────────────────────────────────────────────────┘
```
