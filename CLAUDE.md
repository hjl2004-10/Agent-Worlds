# AI_夸父 开发规范文档 (v2.0 - Skill化重构)

---
> 🌐 **【语言要求】所有 Skill（/qa、/review、/plan-eng-review 等）的最终回答、报告、表格、总结必须使用中文。过程中的内部思考、代码注释、变量名等不限语言。**
>
> ⚠️ **【重要提示】当前项目文件过大，查找时请尽量避免全量查找，避免读完整个上下文。优先使用精确路径或针对性搜索。**
>
> 📝 **【开发环境】不用构建了，现在只在开发环境下进行。前端使用 `npm run dev`，后端直接 `python main.py`。**
>
> 🐍 **【Python 路径】使用系统 Python 3.10+ 或虚拟环境，直接 `python main.py` 启动。**
>
> 🗂️ **【素材库】像素素材统一放在 `static/public/` 下使用。**
---

## Worktree 多开协作 (按需启用)

需要前后端并行开发时，用 git worktree 创建独立副本，避免两个 Claude Code 同时写同一文件冲突。

**创建**: `git worktree add ../kuafu-frontend -b frontend-dev`
**合并**: `git merge frontend-dev`
**清理**: `git worktree remove ../kuafu-frontend && git branch -d frontend-dev`

**通信机制**: 使用共享目录下的 `mailbox.md` 作为实例间邮箱，需要对方配合时写到对应区域。

---

这是一个基于**作用域分层（Scope-Based Layering）**的 AI_OS 系统开发规范文档。

---

## Skill 索引

特定任务场景请加载对应的 Skill 文件：

| Skill | 触发场景 | 文件路径 |
|-------|----------|----------|
| **工具开发** | 添加新工具、修改工具定义、新增对话类型 | [.claude/skills/tool-development.skill.md](.claude/skills/tool-development.skill.md) |
| **精灵图系统** | 添加角色精灵图、修改渲染逻辑、处理方向/动画 | [.claude/skills/sprite-system.skill.md](.claude/skills/sprite-system.skill.md) |
| **部署安全** | 部署到服务器、新增后端/前端功能、本地正常服务器出Bug | [.claude/skills/deployment-safety.skill.md](.claude/skills/deployment-safety.skill.md) |

---

## 0. NPC 角色 & Skill Prompt 编写规范 (重要！)

⚠️ **提示词质量直接决定 NPC 行为质量。以下是从实际运行中总结的要点。**

### 0.1 角色 description 编写要点

| 要点 | 说明 | 反面案例 |
|------|------|----------|
| **聚焦职责边界** | 明确写"你只负责X"，不要泛泛描述 | "你是画师，什么都能做" |
| **禁止闲聊** | 写明"完成工作后立即结束对话，不要互夸、总结、回顾" | 不加限制导致 NPC 互夸 20 轮 |
| **被动等待 vs 主动触发** | 需要用户指令才行动的角色，写"等待用户或上游角色的明确指令才开始工作" | 编剧没收到指令就自行创作 |
| **输出格式约束** | 规定输出 JSON 的字段和格式，不要让 NPC 自由发挥 | 格式不统一导致下游解析失败 |

### 0.2 Skill prompt.md 编写要点

| 要点 | 说明 |
|------|------|
| **完成条件必须明确** | 写清"完成后做X（invoke_npc/保存文件），然后停止" |
| **不要重复执行** | 写"先检查产物是否已存在，已存在则跳过" |
| **invoke_npc 失败处理** | 写"如果 invoke_npc 失败（对方忙），告知用户，不要反复重试" |
| **token 节约** | 写"回复简洁，不加 emoji，不做总结回顾，不重复已说过的内容" |
| **风格前缀统一** | 协作链中的画风描述、命名规范等，在上游 prompt 中统一定义，下游继承 |

### 0.3 协作链 Skill 的特殊要求

当多个 NPC 通过 invoke_npc 组成协作链（如 编剧→分镜→画师→排版）时：

```
【协作链 Prompt 模板要点】
1. 明确上游产物路径: "读取 workspace/comic/script.json"
2. 明确下游交接: "完成后 invoke_npc 调用「XX角色」，传递产物路径"
3. 失败处理: "invoke_npc 失败则停止，告诉对话对象让他转告"
4. 完成即止: "交接完毕后不再主动发言，等待下一个任务"
5. 幂等检查: "开始前检查产物是否已存在，避免重复劳动"
```

### 0.4 base_initiative 设置建议

| 角色类型 | base_initiative | 说明 |
|----------|----------------|------|
| 需要用户指令的角色 | `-1` | 不主动发起对话，只响应 |
| 协作链中间角色 | `-1` | 只通过 invoke_npc 被动触发 |
| 自由行动的 NPC | `2~5` | 会主动碰撞并发起对话 |
| 玩家角色 | `2` | 适中，不会压过 NPC |

> **经验教训**: 漫剧工作室首次运行时，4 个 NPC 都是正数主动值，互相碰撞后自行开始创作、互夸 30+ 轮，浪费大量 token。改为 `-1` 后，只有用户或 invoke_npc 触发才会工作。

---

## 0a. 像素风 UI 素材协作流程

前端使用**像素风 (Pixel Art)** 主题，素材通过 AI 生成。协作流程如下：

### 角色分工
| 角色 | 职责 |
|------|------|
| **Claude** | 编写代码 + 提供 AI 图片生成提示词 + 切割/缩放素材 |
| **用户 (GPT)** | 根据提示词生成透明 PNG 素材，下载后提供路径 |
| **用户** | 审查效果 + 调试反馈 |

### 素材处理规范
1. **生成**: GPT 生成高分辨率像素风素材 (通常 1536x1024)
2. **切割**: Claude 用 Python/PIL 从合图中裁切各元素，去除透明边距
3. **缩放**: NEAREST 插值缩至像素风尺寸 (通常 1/8)，保存到 `static/public/ui/`
4. **集成**: 用 CSS `border-image` 九宫格拉伸 + `image-rendering: pixelated`

### 已有素材目录
```
static/public/ui/
├── flat/                  # UI Essential Pack (按钮/面板/Banner/输入框/进度条)
├── bg-wasteland.png       # 废土背景纹理 (512x512 平铺)
├── bubble-left.png        # 聊天气泡-左 (接收方，青色)
├── bubble-right.png       # 聊天气泡-右 (发送方，绿色)
├── inv-slot-normal.png    # 背包格子-普通态
├── inv-slot-selected.png  # 背包格子-选中态 (金边)
├── inv-slot-empty.png     # 背包格子-空态
├── inv-icon-bag.png       # 背包图标
├── inv-icon-trash.png     # 删除图标
└── inv-badge-qty.png      # 数量徽章
```

### CSS 像素风组件
定义在 `static/src/styles/pixel-ui.css`，通过 class 使用：
- `.pixel-panel--{gray|blue|orange}` — 九宫格面板
- `.pixel-btn--{style1|style2}` + `.pixel-btn--{sm|md|lg}` — 按钮
- `.pixel-banner--{style1~4}` — 横幅标题
- `.pixel-input` / `.pixel-input--dark` — 输入框
- `.pixel-bubble--{left|right}` — 聊天气泡 (支持 Markdown)
- `.pixel-slot--{normal|selected|empty}` — 背包物品格
- `.pixel-bar` / `.pixel-bar__fill` — 进度条

---

## 1. 核心分层架构原则

文件命名后缀代表**业务作用域**与**逻辑粒度**，严禁越级调用。

| 层级 | 文件后缀 | 身份 | 职责定义 | 典型代码 |
| :--- | :--- | :--- | :--- | :--- |
| **总控层** | `无后缀` | 指挥官 | **配置持有**、接口定义、任务分发 | `CONFIG_VAR = 10`, `def interface():` |
| **业务层** | `_l1.py` | 经理 | **个体作用域** (Individual Scope)、流程组装 | `for agent in agents: step1(); step2()` |
| **原子层** | `_l2.py` | 工具 | **原子逻辑** (Atomic Logic)、纯计算（算法等）、无状态 | `return sqrt(x^2 + y^2)`, `return a > b` |

---

## 2. 目录结构与详细职责 (MVP版)

### 📂 `tools/` (工具模块)
* **`llm.py` (总控)**
    * **配置**: `API_KEY`, `MODEL_NAME`。
    * **接口**: `generate(prompt)` -> 调用 L1。
* **`llm_l1.py` (业务)**
    * **职责**: 组装 HTTP 请求头、处理网络异常、返回清洗后的文本。
* **`llm_l2.py` (原子)**
    * **职责**: `parse_json(raw_response)` (单纯的 JSON 解析逻辑)。

### 📂 `env/` (环境模块)
* **`map.py` (总控)**
    * **配置**: `MAP_WIDTH`, `MAP_HEIGHT`。
    * **接口**: `get_distance(a, b)` -> 调用 L1。
* **`map_l1.py` (业务)**
    * **职责**: 接收两个 NPC 对象，提取坐标属性，调用 L2 算距。
* **`map_l2.py` (原子)**
    * **职责**: `math_dist(x1, y1, x2, y2)` (欧几里得公式)。

### 📂 `core/` (核心内核)

#### 1. 交互系统 (`core/social`)
* **`social.py` (总控)**
    * **配置**: `CONTACT_THRESHOLD = 2.0` (接触距离)。
    * **接口**: `run(npcs)` -> 调用 L1。
* **`social_l1.py` (个体业务)**
    * **职责**: 遍历 NPC 列表 -> 调 `map` 拿距离 -> 调 L2 判接触 -> 调 L2 判主动 -> 调 `llm` 说话 -> 调 `mem` 存。
* **`social_l2.py` (原子)**
    * **职责**:
        * `is_contact(dist, limit)` -> `bool`
        * `compare_initiative(val_a, val_b)` -> `winner_obj`

#### 2. 驱动系统 (`core/drive`)
* **`drive.py` (总控)**
    * **配置**: `MAP_BOUNDARY` (边界限制)。
    * **接口**: `update_all(npcs)` -> 调用 L1。
* **`drive_l1.py` (个体业务)**
    * **职责**: 遍历 NPC 列表 -> 调 L2 算新坐标 -> 更新 `npc.x/y`。
* **`drive_l2.py` (原子)**
    * **职责**: `calc_random_walk(x, y, step_size)` -> `(new_x, new_y)`。

#### 3. 记忆系统 (`core/mem`)
* **`mem.py` (总控)**
    * **配置**: `LOG_PATH`。
    * **接口**: `remember(npc, content)`。
* **`mem_l1.py` (个体业务)**
    * **职责**: 格式化日志 -> 写入对应 NPC 的内存列表。
* **`mem_l2.py` (原子)**
    * **职责**: `format_string(time, name, content)` -> `str`。

### 📂 `body/` (实体定义)
* **`npc.py` (容器)**
    * **职责**: 定义 `Agent` 类。
    * **内容**: 仅包含属性 (`name`, `initiative`, `x`, `y`, `memory`)，**无方法**。

### 📂 `root` (根目录)
* **`main.py` (启动器)**
    * **职责**:
        1.  **Boot**: `npc.load()`, `llm.init()`.
        2.  **Loop**: `drive.update_all()` -> `social.run()`.

---

## 3. HJL 数据格式标准

每一个 `.hjl` 文件（无论是个体还是国家）必须包含三大根节点：

```json
{
  "header": {
    "version": "v1.0",
    "type": "INDIVIDUAL",     // INDIVIDUAL | GROUP | NATION
    "uuid": "npc_001",
    "parent_id": "group_A"    // 链接上级社会节点 (SMP协议基础)
  },
  "attributes": {             // 【驱动层数据源】
    "name": "Alice",
    "drive_modifiers": {      // 驱动敏感度矩阵 (HJL转化法则系数)
      "time_sens": 1.2,       // 时间敏感度
      "space_sens": 0.8,      // 空间敏感度
      "random_sens": 0.5      // 随机/意外敏感度
    },
    "constraints": ["NO_KILL"] // 法律/伦理锁
  },
  "graph": {                  // 【记忆层数据源】(动态知识图谱 DKGM)
    "nodes": [ ... ],         // 事件、人物、地点
    "edges": [                // 关系链
      { "source": "A", "target": "B", "weight": 0.9, "decay": 0.05 }
    ]
  }
}
```

### 目录结构 (分形数据库)

数据存储需体现社会层级的**分形 (Fractal)** 特性：

```text
data/
├── world.hjl           # 【世界层】 物理常数、绝对时间
│
├── nations/            # 【宏观层】 法律、历史、文化基调
│   └── nation_001.hjl
│
├── groups/             # 【中观层】 社区共识、SMP共享池
│   └── group_101.hjl
│
└── individuals/        # 【微观层】 个体记忆、性格参数
    ├── npc_001.hjl
    └── npc_002.hjl
```

---

## 4. 记忆系统：RAM vs 持久化 (重要！)

⚠️ **这是最容易混淆的概念，请务必理解！**

### 4.1 两种数据存储

| 类型 | 存储位置 | 生命周期 | API 接口 |
|------|----------|----------|----------|
| **RAM Buffer** | `npc.memory['ram_buffer']` (内存) | 对话期间瞬时存在，对话结束即清空 | `/api/conversation/ram/{npc_name}` |
| **历史记忆** | `data/individuals/{name}.hjl` (文件) | 永久持久化 | `/api/memory/{npc_name}` |

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

### 4.3 前端实时对话 vs 历史记忆 (UI分离)

前端 **必须将两者分开显示**，不能混在一起：

| 区域 | 数据源 | 更新方式 | 用途 |
|------|--------|----------|------|
| **实时对话区** (PlayerInput) | `/api/conversation/ram/{npc_name}` | 轮询 (3秒) | 显示当前正在进行的对话 |
| **记忆区** (MemoryChat) | `/api/memory/{npc_name}` | 加载时获取 | 显示历史记忆 (HJL持久化) |

**为什么分离？**
- 历史记忆 (HJL) 只在**系统停止时**才更新，对话期间不会变化
- 实时对话 (ram_buffer) 在对话期间**持续更新**
- 两者生命周期不同，混在一起会导致逻辑混乱

### 4.4 常见错误

❌ **错误1**：在 MemoryChat 中轮询 `/api/memory`
- HJL 文件只有系统停止时才更新，轮询无意义

❌ **错误2**：试图合并实时对话和历史记忆
- 数据源不同、生命周期不同，必须分开显示

❌ **错误3**：对话结束后还轮询 ram_buffer
- 对话结束后 ram_buffer 被清空，应该停止轮询

### 4.5 代码示例

```python
# social_l1.py 中的数据流
npc.memory['ram_buffer'] = []  # 对话开始时清空
npc.memory['ram_buffer'].append({"role": "user", "content": "..."})  # 对话中累积
mem.persist(npc, f"{npc.name.lower()}.hjl")  # 对话结束时持久化
```

```tsx
// PlayerInput.tsx - 实时对话区 (轮询 ram_buffer)
useEffect(() => {
  if (!speaker) return;  // 没有对话就不轮询

  const poll = async () => {
    const { data } = await godApi.getRamBuffer(speaker);
    if (data.status === 'ok') {
      setMessages(data.items);  // 更新实时对话
    }
  };

  const id = setInterval(poll, 3000);
  return () => clearInterval(id);
}, [speaker]);

// MemoryChat.tsx - 记忆区 (只加载一次历史)
useEffect(() => {
  const load = async () => {
    const { data } = await godApi.getMemory(npcName);
    if (data.status === 'ok') {
      setMessages(data.items);  // 只加载一次，不轮询
    }
  };
  load();
}, [npcName]);
```

---

## 5. Skill / 工具 / MCP 系统 (重要！)

⚠️ **NPC 的"能力"由三个独立来源组成，互不干扰，按优先级合并。**

### 5.1 三个工具来源

| 来源 | HJL 字段 | 内存键 | 说明 |
|------|----------|--------|------|
| **手动配置工具** | `attributes.tools` | `rom_tools` | 前端配置的本地工具名列表 (如 `["goto_location", "send_qq_notify"]`) |
| **Skill 系统** | `attributes.skills` | `rom_tools` (覆盖合并) + `rom_skills_prompts` + `rom_tool_skill_map` | Skill 包含工具+提示词+MCP，加载时解析合并 |
| **MCP 服务器** | `attributes.mcp_servers` | `mcp_servers` (配置) + `mcp_tool_defs` (运行时) | 外部工具协议，**需手动连接** |

### 5.2 Skill 系统

Skill 是"工具+提示词+MCP"的打包单元，存储在 `data/skills/{name}/` 目录下：
```
data/skills/
└── web-browse/
    ├── config.json    # {name, description, tools, mcp_server}
    └── prompt.md      # 完整的技能使用说明
```

**加载流程** (loader_l1.py):
```
HJL skills: ["web-browse"]
    ↓ resolve_skills_for_npc()
    ├─ rom_tools = [合并后的工具列表]
    ├─ rom_tools_prompt = "技能摘要" (放入 system prompt)
    ├─ rom_skills_prompts = {"web-browse": "完整prompt"} (按需注入)
    ├─ rom_tool_skill_map = {"browser_navigate": "web-browse"} (反向映射)
    └─ mcp_servers = [skill 带的 MCP 配置]
```

**按需注入机制**: Skill 的完整 prompt 不在初始对话中注入（太长）。而是在 NPC 首次使用该 skill 的工具时，通过 `tool_result` 附带注入。见 `social_l1._chat_with_tool_loop` 中的 `activated_skills` 逻辑。

### 5.3 MCP 连接机制 (懒加载设计)

⚠️ **MCP 启动时不自动连接，需要 NPC 在对话中主动调用 `connect_mcp` 工具。**

```
启动时:
  loader_l1 → mcp_servers = [{name, url}]   ← 只记录配置
              mcp_tool_defs = []              ← 空！

运行时 (NPC 调用 connect_mcp):
  tool_l1 → connect_npc_servers()
           → mcp_tool_defs = [工具定义列表]  ← 填充
```

**为什么不自动连接？**
- MCP 服务器可能未启动、网络不通
- 避免启动时阻塞
- NPC 按需连接更灵活

**常见误解**: `mcp_tool_defs` 为空不是 bug，是因为还没 connect_mcp。

### 5.4 提示词组装完整链路

对话时 `prompt_l1.assemble()` 按以下顺序组装 messages：

```
1. [system] rom_prompt 模板按索引渲染 (变量替换)
   ├─ {lore_text}     → 世界观+场景
   ├─ {time_str}      → 当前时间
   ├─ {persona}       → rom_personality
   ├─ {listener_name} → 对话对象名
   ├─ {relation_desc} → 关系描述
   ├─ {tools_prompt}  → rom_tools_prompt (Skill摘要或手动配的工具说明)
   ├─ {tasks_text}    → 待办任务列表
   └─ {memory_text}   → 历史记忆 (5相关+3其他)

2. [system] task_tools_text  → 任务动态工具说明 (有待办任务时才有)
3. [system] npc_tools_text   → NPC配置工具说明 (rom_tools 非空时才有)
4. [user/assistant] ram_buffer → 当前对话流
5. [user] trigger → 触发语 ("你遇到了XX，打招呼")
```

### 5.5 工具链门控 (_should_use_tools)

决定是否使用 Anthropic 原生工具协议（而非纯文本输出）：

```
条件全部满足才启用:
  1. 渠道 provider == "claude"  (zhipu/volcano/local)
  AND 以下任一:
  2a. rom_tools 非空
  2b. mcp_tool_defs 非空 (已 connect_mcp)
  2c. pending_tasks 中有 tool_hint
```

如果不启用，LLM 只输出文本，工具调用靠 `tool_invoke_sync` 文本解析。

### 5.6 工具定义合并 (_chat_with_tool_loop)

启用工具模式后，传给 LLM 的 tools 列表：
```
tools = task_tools          ← 任务相关工具定义
      + context['npc_tools'] ← rom_tools 定义 + mcp_tool_defs
      + extra_tools          ← 临时工具 (如地点对话的 arrived_at)
      (去重)
```

### 5.7 NPC 配置要点

要让 NPC 能用工具，需要确保：

| 需求 | 配置项 | 注意事项 |
|------|--------|----------|
| 本地工具 | `attributes.tools: ["tool_name"]` | 工具必须在 TOOL_REGISTRY 中注册 |
| Skill 工具 | `attributes.skills: ["skill_name"]` | Skill 会覆盖 tools 字段 |
| MCP 工具 | `attributes.mcp_servers: [{name, url}]` | **必须在对话中先 connect_mcp** |
| 工具模式 | `llm_config.channel` 的 provider 必须是 `"claude"` | zhipu/volcano/local 都行 |

---

## 6. API 路由模块化 (api/)

main.py 只保留启动/循环逻辑，路由拆分到 `api/` 子模块：

| 模块 | 路由前缀 | 职责 |
|------|----------|------|
| `api/status.py` | `/api/status`, `/api/map`, `/api/events` | 状态/地图/事件 |
| `api/god.py` | `/api/god/*` | 上帝模式控制 |
| `api/npc.py` | `/api/npc/*` | NPC 管理/配置/导入导出 |
| `api/conversation.py` | `/api/conversation/*`, `/api/player/*` | 对话/玩家输入/记忆 |
| `api/tools_api.py` | `/api/tools/*`, `/api/skills/*`, `/api/mcp/*` | 工具/技能/MCP/市场 |
| `api/world.py` | `/api/world/*`, `/api/scene/*` | 世界/场景管理 |
| `api/tasks.py` | `/api/tasks/*`, `/api/timers/*` | 任务/定时器 |
| `api/mailbox.py` | `/api/mailbox/*`, `/api/form/*` | 邮箱/表单 |
| `api/misc.py` | `/api/llm/*`, `/api/sprites/*` | LLM渠道/精灵图 |
| `api/auth.py` | (中间件) | Token 认证 + CORS |
| `api/_state.py` | (内部) | 全局状态引用 + 事件推送 |

共享状态通过 `api/_state.py` 注入，命令通过 `core/dispatcher.py` handler dict 分发。

---

## 每次做完一个板块级的东西更新更新日志.txt
