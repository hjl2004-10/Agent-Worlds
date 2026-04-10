# 夸父 Agent OS — Harness 架构设计方案

> 基于 2026 年 Harness Engineering 行业共识，结合夸父项目现状的系统性架构设计。

---

## 核心定位

行业核心公式：**coding agent = AI model + harness**

夸父的对应：

> **NPC Agent = LLM 模型 + 夸父 Harness（运行时编排系统）**

夸父本质上就是一个 **Agent Harness / Agent OS**，为多个 NPC Agent 提供"操作系统"级别的运行环境。现有的分层架构（总控→业务→原子）已经暗合了 Harness Engineering 的核心理念，但可以用这套框架重新审视和强化。

---

## 一、三层映射：Harness 论文 ↔ 夸父现有架构

论文（arxiv 2603.05344）把 Agent 运行架构分三层：

| Harness 论文层 | 类比 | 夸父对应 | 现状 |
|---|---|---|---|
| **Scaffolding（脚手架）** | BIOS/引导 | `loader_l1` + HJL 加载 + Skill 解析 + prompt 模板编译 | 已有，较完善 |
| **Harness（运行时编排）** | OS 内核 | `social_l1`(对话循环) + `tool_l1`(工具执行) + `mcp_manager`(外部工具) + `dispatcher`(命令分发) | 已有，需强化 |
| **Context Engineering（上下文工程）** | 内存管理 | `prompt_l1.assemble()` + RAM buffer + HJL 记忆 | 已有，需优化 |

**结论：夸父已经是一个 Harness 系统，只是还没有从这个视角去系统性地设计和优化。**

---

## 二、OS 类比

Philipp Schmid 提出的计算机类比，映射到夸父：

| 计算机组件 | Agent 对应物 | 夸父对应 |
|---|---|---|
| CPU | 模型（原始算力） | LLM 渠道（Claude/智谱/火山） |
| 内存 | 上下文窗口（易失的工作记忆） | RAM Buffer |
| 硬盘 | 持久存储 | HJL 文件 + Graph 图谱 |
| 操作系统 | Agent Harness | 夸父核心（core/ + tools/） |
| 应用程序 | Agent | 每个 NPC 实例 |
| 驱动程序 | 工具接口 | Tool Registry + MCP Client |
| 进程管理 | Agent 生命周期 | social_l1 对话循环 + task 调度 |

---

## 三、七个杠杆的夸父实践

### 杠杆 1：AGENTS.md — NPC 的"入职手册"

**现状**：夸父用 HJL 文件的 `attributes` + `prompt 模板` 充当这个角色。

**强化方案**：引入 **harness_rules（行为护栏）** 字段

```json
{
  "attributes": {
    "harness_rules": {
      "constraints": ["NO_KILL", "NO_SPOILER"],
      "style_guide": "说话简短，爱用比喻",
      "failure_rules": ["遇到不确定的事就说不知道"],
      "tool_limits": {
        "max_tools_per_turn": 3,
        "max_tool_rounds": 5
      }
    }
  }
}
```

核心思想：**每次 NPC 犯了一个不符合人设的错，就往 harness_rules 里加一条规则**。这就是 Mitchell Hashimoto 说的改进飞轮。

### 杠杆 2：确定性约束 — 硬护栏

**现状**：`constraints: ["NO_KILL"]` 基本是软约束（靠提示词）。

**强化方案**：增加 **Output Guard 确定性拦截层**

```
                    NPC 输出
                       ↓
              ┌─────────────────┐
              │  Output Guard   │  ← 新增：确定性检查
              │  (tool_l2 级)   │
              ├─────────────────┤
              │ 1. 违禁词检测    │  → 硬拦截，不调 LLM
              │ 2. 工具权限校验  │  → NPC 只能用配置的工具
              │ 3. 输出长度限制  │  → 防止 token 爆炸
              │ 4. 循环检测      │  → 防止 tool loop 死循环
              └─────────────────┘
                       ↓
                  放行 / 拦截重试
```

代码位置：在 `social_l1._chat_with_tool_loop` 的工具执行循环中加入 guard 层。不靠 prompt 说"请遵守"，而是**代码级的 if/else 硬拦截**。

### 杠杆 3：工具精简 — 少即是多

**行业数据**：Vercel 从 15 个工具砍到 2 个，准确率从 80% 升到 100%。

**强化方案**：

- 每个 NPC 的工具上限：最多 8 个
- 工具分级：核心工具（始终可用）+ 情境工具（特定场景注入）
- 在 `_should_use_tools` 基础上加 `_select_tools` 做动态精简

```python
# tool_l1.py 新增
def select_tools_for_context(npc, context) -> list:
    """根据当前情境精选工具子集，而非全量传入"""
    all_tools = npc.memory['rom_tools'] + npc.memory.get('mcp_tool_defs', [])

    # 规则1：任务相关工具优先
    task_tools = [t for t in all_tools if t in context.get('task_hints', [])]
    # 规则2：场景相关工具次之
    scene_tools = [t for t in all_tools if t in SCENE_TOOL_MAP.get(context['scene'], [])]
    # 规则3：总量不超过 8 个
    return (task_tools + scene_tools)[:8]
```

### 杠杆 4：Sub-Agent 隔离

**现状**：每个 NPC 本身就是独立 Agent，有自己的上下文窗口（RAM buffer）。

**远期方案**：对于复杂任务，允许 NPC 内部再拆分 sub-agent

```
NPC Alice 收到任务："调研竞品并写报告"
    ↓
Planner（Alice 主线程）→ 拆分子任务
    ├── Worker 1：用 browser 工具爬取数据（独立上下文）
    ├── Worker 2：用 knowledge 工具查内部资料（独立上下文）
    └── Alice 主线程：汇总 Worker 结果，生成报告
```

当前 NPC 任务复杂度不需要，**架构上预留口子即可**。

### 杠杆 5：反馈循环 — 让 NPC 自己验证

**现状**：NPC 执行工具后能看到 tool_result，缺乏"自我验证"机制。

**强化方案**：

```
NPC 调用工具
    ↓
工具返回结果
    ↓
┌──────────────────────┐
│  Result Validator    │  ← 新增
│  (social_l2 级)      │
├──────────────────────┤
│ 1. 工具是否报错？     │  → 告知 NPC 重试
│ 2. 结果是否为空？     │  → 提示 NPC 换策略
│ 3. 结果是否超长？     │  → 自动摘要后再给 NPC
│ 4. 是否触发约束？     │  → 拦截并解释原因
└──────────────────────┘
    ↓
清洗后的 tool_result → 回到对话循环
```

### 杠杆 6：CI 限速 — 工具调用次数上限

**对应 Stripe 的"CI 最多跑两轮"思路**：

```python
# social_l1.py
MAX_TOOL_ROUNDS = 5  # 最多 5 轮工具调用
# 超过后：停止工具模式，让 NPC 用文本总结当前进度
```

### 杠杆 7：垃圾回收 / 熵管理

**现状**：记忆系统有 `decay` 权重衰减，但没有主动清理。

**强化方案**（利用现有 timer 系统）：

| 清理任务 | 频率 | 逻辑 |
|---|---|---|
| 记忆清理 | 每日 | decay < 0.1 的边自动归档 |
| RAM 压缩 | 每次对话 | ram_buffer 超过 N 条时自动摘要 |
| 关系修剪 | 每周 | 长期未互动的关系降权 |
| HJL 一致性检查 | 每周 | 检测 graph 中引用的已删除节点 |

---

## 四、整体架构图

```
┌─────────────────────────────────────────────────────┐
│                    夸父 Agent OS                     │
│                                                      │
│  ┌─────────────────────────────────────────────────┐│
│  │          Scaffolding 脚手架层                    ││
│  │                                                  ││
│  │  HJL Loader → Skill 解析 → Prompt 编译          ││
│  │  工具注册 → MCP 配置 → 世界观加载                 ││
│  │  (启动时一次性执行)                               ││
│  └─────────────────────────────────────────────────┘│
│                         ↓                            │
│  ┌─────────────────────────────────────────────────┐│
│  │          Harness 运行时编排层                     ││
│  │                                                  ││
│  │  ┌──────────┐  ┌──────────┐  ┌───────────┐     ││
│  │  │Drive 驱动│  │Social 社交│  │Task 任务  │     ││
│  │  │  移动     │  │  对话循环 │  │  调度执行 │     ││
│  │  └──────────┘  └──────────┘  └───────────┘     ││
│  │         ↕              ↕             ↕          ││
│  │  ┌──────────────────────────────────────────┐   ││
│  │  │          Guard 护栏层 (新增)              │   ││
│  │  │  输出检查 | 工具权限 | 循环检测 | 限速    │   ││
│  │  └──────────────────────────────────────────┘   ││
│  │         ↕              ↕             ↕          ││
│  │  ┌──────────────────────────────────────────┐   ││
│  │  │          Tool 工具执行层                  │   ││
│  │  │  本地工具 | Skill工具 | MCP外部工具       │   ││
│  │  └──────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────┘│
│                         ↓                            │
│  ┌─────────────────────────────────────────────────┐│
│  │       Context Engineering 上下文工程层           ││
│  │                                                  ││
│  │  Prompt 组装 → Token 预算 → 记忆检索             ││
│  │  RAM Buffer → HJL 持久化 → Graph 衰减            ││
│  │  (每次对话动态构建)                               ││
│  └─────────────────────────────────────────────────┘│
│                                                      │
│  ┌─────────────────────────────────────────────────┐│
│  │           反馈飞轮 (贯穿全层)                    ││
│  │                                                  ││
│  │  NPC行为异常 → 人类诊断 → 更新HJL规则/          ││
│  │  调整Prompt模板/加强Guard → NPC下次不再犯        ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

---

## 五、与行业观点的对齐

| 行业观点 | 夸父的实践 |
|---|---|
| "仓库就是大脑"（OpenAI） | HJL 文件 + data/ 目录就是 NPC 的全部知识来源 |
| "代码要对 Agent 可读"（OpenAI） | 分层架构（总控→L1→L2）+ 严格命名规范 |
| "自主性分级"（OpenAI） | NPC 的工具权限、MCP 懒加载、Skill 按需注入 |
| "约束比指令更有效"（Cursor） | 从"prompt 里写规则"升级到"代码里硬拦截" |
| "工具越少越好"（Vercel） | 工具动态精选，上限 8 个 |
| "Harness 要轻，能拆"（Philipp Schmid） | L2 原子层无状态，随时可替换 |
| "Start Simple, Build to Delete" | "复用优先，不动辄建新引擎"的项目原则 |
| "Blueprint 确定性+Agentic 混合"（Stripe） | dispatcher 确定性分发 + social_l1 Agentic 对话 |
| "每个 Harness 错误都反哺回仓库"（Hashimoto） | harness_rules 飞轮机制 |

---

## 六、Big Model vs Big Harness — 夸父的立场

文章提到两大阵营：

- **Big Model 派**（Claude Code / Noam Brown）："模型够强就不需要复杂 Harness"
- **Big Harness 派**（LlamaIndex / Stripe）："Harness 就是一切"

**夸父的立场：务实的中间路线。**

夸父的 NPC 不是编程 Agent，而是**角色扮演 Agent**。这意味着：

1. **模型能力很重要**（决定对话质量和工具调用准确性），但
2. **Harness 不可替代**（NPC 的人设一致性、记忆管理、社会关系、世界观约束——这些不是模型能自动搞定的）
3. **Harness 要轻**（Manus 6 个月重构 5 次的教训），保持现有的分层架构，渐进增强

核心原则：**护栏悖论 — 模型越强，NPC 越自主，约束系统越重要。**

---

## 七、实施优先级

| 优先级 | 任务 | 投入 | 收益 | 涉及文件 |
|---|---|---|---|---|
| P0 | Guard 护栏层 | 小 | 大 | `social_l1.py`, 新增 `guard_l2.py` |
| P1 | 工具动态精选 | 小 | 中 | `tool_l1.py` |
| P1 | harness_rules HJL 字段 | 小 | 大 | HJL schema, `loader_l1.py`, `prompt_l1.py` |
| P2 | Result Validator | 中 | 中 | `social_l1.py`, `tool_l2.py` |
| P2 | 熵管理定时任务 | 中 | 中 | `timer_l1.py`, `mem_l1.py` |
| P3 | Sub-Agent 架构 | 大 | 远期 | 新模块 |

---

## 八、关键数据参考

来自文章的行业数据，支撑设计决策：

| 数据 | 来源 | 对夸父的启示 |
|---|---|---|
| 同模型换 Harness，成功率 42%→78% | Nate B Jones | Harness 设计比换模型更值得投入 |
| 工具 15→2，准确率 80%→100% | Vercel | 工具要精不要多 |
| AGENTS.md 控制在 60 行内 | ETH Zurich | NPC prompt 模板不宜过长 |
| CI 最多跑两轮 | Stripe | 工具调用要有硬上限 |
| 5 个月 100 万行零手写代码 | OpenAI Codex | Harness 成熟后 Agent 自主性可以很高 |
| Harness 6 个月重构 5 次 | Manus | Harness 要轻，要能快速迭代 |

---

*文档版本：v1.0 | 2026-03-28 | 基于《观点.txt》Harness Engineering 行业分析*
