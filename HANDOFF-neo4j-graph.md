# 任务交接：给夸父提示词系统增加 Neo4j 知识图谱块

> 本文档自包含，新会话/新环境拿到即可接手，无需回看原对话历史。
> 项目：夸父 AI_OS（GitHub 仓库 **Agent-Worlds**，作者 hjl2004-10）。

---

## 0. 一句话任务

给 Agent-Worlds 的提示词系统**新增一个「知识图谱」块**：用 Neo4j 存 NPC 的社交关系、事件经历链、物品流转等**关系型知识**，在对话时按情境检索出相关子图，作为一个新的提示词片段注入 system prompt。

**这是新功能，不是数据迁移**——现有的 `rom_groups` / `hdd_history` / `inventory` 只是实验性实现，不碰、不迁。Neo4j 图谱是独立的新数据源。

---

## 1. 已完成的环境工作（本次会话）

### 1.1 Agent-Worlds 部署
- **位置**：`/root/部署文件夹/Agent-Worlds`（`git clone https://github.com/hjl2004-10/Agent-Worlds`）
- **systemd 服务**：`agent-worlds.service`，开机自启。管理 `systemctl {status|restart} agent-worlds`，日志 `journalctl -u agent-worlds -f`
- **端口**：5000，前后端同源（后端托管 `static/dist`）
- **外网**：`https://kuafuai.top`（nginx 反代 443→5000，letsencrypt 证书；该域名原挂 Neo4j 已让位）
- **venv**：`Agent-Worlds/venv`（系统 python3 3.12）
- **LLM 配置**：`config/llm.json` 已带 key（deepseek/volcano/zhipu/local/embedding_zhipu/image_zhipu），默认 deepseek。认证未开（`config/auth.json` 的 api_token 为空）
- **重启服务后注意**：git 仓库不带运行时数据（`dist/`、`config/llm.json`、`data/individuals/` 都在 .gitignore），拉新代码后需重新 `npm run build` 且别覆盖这些

### 1.2 Docker Neo4j（为本任务准备的目标库）
- **容器**：`neo4j-2`，镜像 `neo4j:latest`（社区版 2026.05.0，与本机原 Neo4j 同版本）
- **端口**：`7475`(HTTP Browser) / `7688`(Bolt)——**特意避开本机原 Neo4j 的 7474/7687**（原实例被"代码树"项目占用，不能动）
- **账号**：`neo4j` / `kuafuai`
- **连接串**：`bolt://localhost:7688`，用户 `neo4j`，密码 `kuafuai`
- **数据持久化**：docker 命名卷 `neo4j2-data`(/data)、`neo4j2-logs`(/logs)
- **开机自启**：`--restart unless-stopped`
- **管理**：`docker {logs|restart} neo4j-2`；执行 Cypher：`docker exec -it neo4j-2 cypher-shell -u neo4j -p kuafuai`
- **踩过的坑**：①新版 Neo4j 密码要求≥8位，`kuafuai`(7位) 靠环境变量 `NEO4J_dbms_security_auth__minimum__password__length=7` 放宽；②Docker CLI 不支持 `docker pull --progress`；③Docker 走 mihomo 代理拉镜像（drop-in `/etc/systemd/system/docker.service.d/http-proxy.conf` 设 `HTTP(S)_PROXY=127.0.0.1:7897`）

### 1.3 现有提示词系统调研结论（重点，接手必读）
**组装机制**：
- 入口 `core/prompt/prompt.py: build()` → `prompt_l1.assemble()` → `prompt_l2.build_context()` 构建上下文变量
- 每个 NPC 的 hjl 里 `attributes.prompt` 是个**模板数组**，元素是带占位符的片段（如 `"{persona}"`、`"[你的记忆]:\n{memory_text}"`）
- 对话时遍历该数组，用 `prompt_l2.render()` 做**字符串替换**（`{key}`→值），非空片段按顺序拼成多条 system message
- 之后追加 task_tools_text、npc_tools_text、ram_buffer（当前对话流）、trigger（触发语）

**现有的提示词块（占位符）**：
`{lore_text}`(世界观+场景)、`{time_str}`/`{period}`(时间)、`{persona}`(人设)、`{listener_name}`/`{relation_desc}`(对话对象+关系)、`{tools_prompt}`(工具)、`{extra_prompt}`、`{tasks_text}`/`{task_tools_text}`(任务)、`{memory_note}`(笔记)、`{memory_text}`(历史记忆)

**记忆系统现状**（`core/mem/mem_l1.py`）：
- `ram_buffer`：对话期间的内存缓冲，对话结束转存
- `hdd_history`：持久化历史（文本列表），落盘到 hjl 的 `memory.history`
- `format_memory()`：按对话对象名过滤，取相关 N 条 + 其他 N 条注入

**关系/事件/背包现状（痛点，Neo4j 要补的）**：
- 人物关系 → `rom_groups`，**扁平字符串**（"朋友:Bob"），`get_relation_desc()` 只能命中当前对话对象，查不了"我认识谁、亲密度、二度关系"
- 事件/记忆 → `hdd_history`，**纯文本列表**，没有结构化事件链、时序、因果
- 背包 → inventory **键值对**（物品:数量），没有来历/流转
- 设计文档(CLAUDE.md §3)里预留了 `graph` 图谱节点(DKGM)，但**当前实现未启用**，全落在 memory 里

**加 Neo4j 块的接入点（极小，已确认）**：
1. 后端连 neo4j-2：`bolt://localhost:7688`，`neo4j/kuafuai`（需装 `neo4j` Python 驱动到 venv）
2. `core/prompt/prompt_l2.py` 的 `build_context()` 加一个变量 `'graph_text': format_graph(speaker, listener, config)`
3. NPC 的 `attributes.prompt` 数组里加一行 `"{graph_text}"`
4. 新写 `format_graph(speaker, listener, config)`：从 Neo4j 查相关子图 → 格式化成文本（仿照 `format_memory()` 的风格）

---

## 2. 打算做的事（任务本体）

### 2.1 设计共识（已和用户讨论确定）
- **性质**：全新功能，不迁移/不动现有数据
- **探讨焦点**：①图谱该建哪些知识块 ②对话时怎么检索出需要的内容注入

### 2.2 建议建的块（我的主张，待用户最终拍板）
针对「NPC 自主生活」场景，承载的都是现有扁平数据搞不定的**关系型知识**：

1. **社交关系图** — `Person-[关系类型/亲密度/上次互动时间]->Person`
   - 价值：查二度关系、关系随互动衰减、跟谁熟。现有 rom_groups 做不到
2. **事件经历链** — `Event 节点`(时间/地点/参与者/描述) + `时序(NEXT)`/`因果(CAUSED)`/`参与` 边
   - 价值：结构化经历，按人/地/时多维检索，讲得出"前因后果"
3. **物品流转图** — `Item-[OWNS/GAVE/来源]->`
   - 价值：背包带"来历和流转"，支撑交易/赠予/协作

**边界**：地点（`env/map` 已有）、任务（`tools/task` 已有）不进图谱，不重复造。

### 2.3 检索策略（核心，不是全塞）
按**当前情境**捞出相关子图，情境信号：
- **对象是谁** → 取「我和他的关系 + 共同经历」
- **在哪** → 取「此地相关的人和事」
- **在聊什么** → 取对话里被提到的实体（人/物/事）的关联
- **在做什么任务** → 取任务相关的人/物/历史

取法：从关键节点出发 **1–2 跳** + 按权重(亲密度/重要度/时效)排序 + **每块限量**(仿 memory 的 5+3)控 token → 格式化成简短文本注入 `graph_text`。Neo4j 给 name/时间建索引仅加速。

### 2.4 待和用户定的三个关键点（接手后先推进这些）
1. **范围**：上面三块够不够？要加（派系/组织、地点归属）还是减？
2. **检索主信号**：先以**对话对象**为主（和现有 memory 一致），还是以**话题/任务**为主？
3. **写入入口**（新功能图里的数据哪来）——倾向给 NPC 一组工具显式写（`add_relation`/`record_event`/`transfer_item`，由 LLM 在对话中判断"该记"时调用，贴合现有 Skill/工具体系）；备选是对话后自动抽取。需用户定。

---

## 3. 接手后的行动建议
1. 读本文档 §1.3（现有提示词系统）+ §2（设计共识）对齐认知
2. 和用户确认 §2.4 三个关键点（范围 / 检索主信号 / 写入入口）
3. 定稿后：装 neo4j Python 驱动 → 设计节点/边 schema → 写 `format_graph()` 和检索查询 → 加 `{graph_text}` 占位符 → 写入入口(工具) → 测试
4. 改代码遵循项目分层规范：总控(无后缀)/业务(`_l1`)/原子(`_l2`)，路径用 `Path(__file__).resolve()`

---

## 4. 关键文件与环境速查
| 项 | 位置/值 |
|---|---|
| 项目根 | `/root/部署文件夹/Agent-Worlds` |
| 提示词系统 | `core/prompt/prompt.py` / `prompt_l1.py` / `prompt_l2.py` |
| 记忆系统 | `core/mem/mem.py` / `mem_l1.py` / `mem_l2.py` |
| NPC 数据 | `data/individuals/*.hjl`（`attributes.prompt` 是模板数组） |
| NPC 容器定义 | `body/npc.py`（Agent 类，仅属性无方法） |
| 工具注册表 | `tools/tool.py` 的 `TOOL_REGISTRY` |
| 配置 | `config/`（llm.json / auth.json / tool_groups.json） |
| Neo4j 目标库 | `bolt://localhost:7688`，`neo4j/kuafuai`（容器 neo4j-2） |
| 后端启动 | `systemctl restart agent-worlds`（或 `cd 项目 && venv/bin/python main.py`） |
| 外网 | `https://kuafuai.top` |

## 5. 相关长期记忆（同服务器新会话会自动加载）
- `~/.claude/projects/-root/memory/aios-deployment.md` — Agent-Worlds 部署详情
- `~/.claude/projects/-root/memory/docker-neo4j.md` — Docker Neo4j 实例详情
- 若新环境是**不同服务器**：本文件 + 项目代码 + 上述两份记忆内容需一并带走
