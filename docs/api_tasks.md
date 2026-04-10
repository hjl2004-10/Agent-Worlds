# 玩家任务管理 API 对接文档

> 版本: v1.0
> 更新时间: 2026-02-17
> 后端端口: 5000

---

## 一、功能概述

玩家（真人用户）通过前端 UI 给 NPC 下放任务、查看任务、删除任务、标记任务完成。

---

## 二、API 端点列表

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/tasks/assign` | 给 NPC 下放任务 |
| GET | `/api/tasks/{npc_name}` | 查询 NPC 的任务列表 |
| DELETE | `/api/tasks/{npc_name}` | 删除 NPC 的任务 |
| PATCH | `/api/tasks/{npc_name}/complete` | 标记任务完成 |

---

## 三、接口详情

### 3.1 下放任务

**POST** `/api/tasks/assign`

**请求头:**
```
Content-Type: application/json
```

**请求体:**
```json
{
  "target": "Alice",                              // 必填，目标 NPC 名称
  "hint": "查看 Bob 留给你的信",                   // 必填，任务提示内容
  "tool_hint": "read_file: path=letter.txt"       // 可选，工具使用指引
}
```

**成功响应 (200):**
```json
{
  "status": "ok",
  "task": {
    "hint": "查看 Bob 留给你的信",
    "source": "Player",
    "tool_hint": "read_file: path=letter.txt",
    "status": "pending"
  }
}
```

**失败响应:**
```json
{
  "status": "error",
  "message": "Missing target or hint"
}
```
```json
{
  "status": "error",
  "message": "NPC 'XXX' not found"
}
```

**前端调用示例:**
```javascript
async function assignTask(target, hint, toolHint = null) {
  const body = { target, hint };
  if (toolHint) body.tool_hint = toolHint;

  const response = await fetch('/api/tasks/assign', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return response.json();
}

// 使用示例
assignTask('Alice', '去广场等 Bob');
assignTask('Bob', '查看文件', 'read_file: path=letter.txt');
```

---

### 3.2 查询任务列表

**GET** `/api/tasks/{npc_name}`

**路径参数:**
- `npc_name`: NPC 名称（如 Alice、Bob）

**成功响应 (200):**
```json
{
  "status": "ok",
  "npc": "Alice",
  "tasks": [
    {
      "hint": "查看 Bob 留给你的信",
      "source": "Player",
      "tool_hint": "read_file: path=letter.txt",
      "status": "pending"
    },
    {
      "hint": "去广场等 Bob",
      "source": "David",
      "tool_hint": null,
      "status": "done"
    }
  ]
}
```

**前端调用示例:**
```javascript
async function getTasks(npcName) {
  const response = await fetch(`/api/tasks/${npcName}`);
  return response.json();
}

// 使用示例
const data = await getTasks('Alice');
console.log(data.tasks); // 任务数组
```

---

### 3.3 删除任务

**DELETE** `/api/tasks/{npc_name}`

**路径参数:**
- `npc_name`: NPC 名称

**请求头:**
```
Content-Type: application/json
```

**请求体:**
```json
{
  "hint": "信"    // 必填，模糊匹配任务内容（包含此文字的任务都会被删除）
}
```

**成功响应 (200):**
```json
{
  "status": "ok",
  "deleted": 2    // 删除的任务数量
}
```

**前端调用示例:**
```javascript
async function deleteTask(npcName, hintKeyword) {
  const response = await fetch(`/api/tasks/${npcName}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hint: hintKeyword })
  });
  return response.json();
}

// 使用示例：删除 Alice 所有包含"信"的任务
const result = await deleteTask('Alice', '信');
console.log(`删除了 ${result.deleted} 个任务`);
```

---

### 3.4 标记任务完成

**PATCH** `/api/tasks/{npc_name}/complete`

**路径参数:**
- `npc_name`: NPC 名称

**请求头:**
```
Content-Type: application/json
```

**请求体:**
```json
{
  "hint": "信"    // 必填，模糊匹配任务内容
}
```

**成功响应 (200):**
```json
{
  "status": "ok",
  "completed": 1    // 标记完成的任务数量
}
```

**前端调用示例:**
```javascript
async function completeTask(npcName, hintKeyword) {
  const response = await fetch(`/api/tasks/${npcName}/complete`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hint: hintKeyword })
  });
  return response.json();
}

// 使用示例
const result = await completeTask('Alice', '信');
```

---

## 四、辅助接口

### 4.1 获取 NPC 列表

**GET** `/api/npcs`

**响应:**
```json
[
  { "name": "Alice", "x": 40.5, "y": 13.1, ... },
  { "name": "Bob", "x": 44.9, "y": 56.1, ... },
  ...
]
```

### 4.2 获取工具列表

**GET** `/api/tools`

**响应:**
```json
{
  "status": "ok",
  "tools": {
    "read_file": {
      "description": "读取文本文件内容",
      "params": {
        "path": {"type": "string", "description": "文件路径"},
        "start_line": {"type": "integer", "minimum": 1},
        "end_line": {"type": "integer", "minimum": -1},
        "max_chars": {"type": "integer", "minimum": 1, "maximum": 200000}
      },
      "required": ["path"]
    },
    "write_file": {
      "description": "创建或覆写/追加文本文件",
      "params": {...},
      "required": ["path", "content"]
    },
    "edit_text": {
      "description": "精确编辑文本文件: 替换/插入/删除行",
      "params": {...},
      "required": ["path", "action"]
    }
  }
}
```

**用途**: 前端可以用这个接口动态生成工具选择器，让用户通过 UI 选择工具而不是手动输入。

---

## 五、任务对象结构

```typescript
interface Task {
  hint: string;        // 任务提示（自然语言）
  source: string;      // 任务来源（"Player" 或其他 NPC 名）
  tool_hint: string | null;  // 工具指引（可选）
  status: "pending" | "done";  // 任务状态
}
```

---

## 六、UI 设计建议

### 6.1 任务管理面板

```
┌─────────────────────────────────────┐
│  任务管理                            │
├─────────────────────────────────────┤
│  目标 NPC: [下拉选择 ▼]              │
│                                      │
│  任务描述: [________________]        │
│                                      │
│  工具指引: [________________] (可选) │
│            例: read_file: path=xxx   │
│                                      │
│  [下放任务]                          │
├─────────────────────────────────────┤
│  当前任务 (Alice):                   │
│  ┌─────────────────────────────┐    │
│  │ [待办] 查看 Bob 的信         │    │
│  │        来源: Player          │    │
│  │        [完成] [删除]         │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ [已完成] 去广场              │    │
│  │          来源: David         │    │
│  │          [删除]              │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

### 6.2 交互流程

1. **下放任务**：选择 NPC → 输入描述 → (可选)输入工具指引 → 点击下放
2. **查看任务**：选择 NPC → 自动加载该 NPC 的任务列表
3. **完成任务**：点击任务卡片上的"完成"按钮
4. **删除任务**：点击任务卡片上的"删除"按钮

### 6.3 工具指引说明（高级功能）

`tool_hint` 字段用于告诉 NPC 如何使用工具完成任务：

| 任务类型 | tool_hint 示例 |
|---------|----------------|
| 读取文件 | `read_file: path=letter.txt` |
| 查看目录 | `read_file: path=.` |
| 写入文件 | `write_file: path=note.txt` |

如果不需要引导 NPC 使用工具，此字段可留空。

---

## 七、错误码

| status | message | 说明 |
|--------|---------|------|
| error | Missing target or hint | 请求缺少必填字段 |
| error | Missing hint | 删除/完成操作缺少匹配关键词 |
| error | NPC 'XXX' not found | 指定的 NPC 不存在 |

---

## 八、测试命令

```bash
# 下放任务
curl -X POST http://localhost:5000/api/tasks/assign \
  -H "Content-Type: application/json" \
  -d '{"target":"Alice","hint":"测试任务"}'

# 查询任务
curl http://localhost:5000/api/tasks/Alice

# 完成任务
curl -X PATCH http://localhost:5000/api/tasks/Alice/complete \
  -H "Content-Type: application/json" \
  -d '{"hint":"测试"}'

# 删除任务
curl -X DELETE http://localhost:5000/api/tasks/Alice \
  -H "Content-Type: application/json" \
  -d '{"hint":"测试"}'
```
