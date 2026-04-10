# 部署安全规范 Skill

---
description: 部署时的常见陷阱与安全规范（路径、SPA、loading状态）
triggers:
  - 部署到服务器
  - 新增后端模块
  - 新增前端功能
  - 遇到"本地正常、服务器出Bug"的问题
---

⚠️ **以下规则必须遵守，否则会导致"本地正常、服务器出 Bug"的问题。**

---

## 1. 后端路径必须使用绝对路径

**规则：所有 Python 模块中的文件/目录路径，必须基于 `Path(__file__).resolve()` 构建，禁止使用相对路径或 `os.path.dirname(__file__)`。**

### 原因

`os.path.dirname(__file__)` 在 `__file__` 为相对路径时可能返回空字符串，导致路径变成依赖 CWD 的相对路径。本地开发时 CWD 恰好是项目目录所以没问题，但服务器上的启动方式（systemd、screen、crontab 等）的 CWD 可能不是项目目录。

### 正确写法

```python
# ✅ 正确 - 始终是绝对路径，无论 CWD 在哪都能找到文件
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = str(_PROJECT_ROOT / "data" / "xxx")

# ❌ 错误 - 依赖 CWD，服务器上可能找不到
DATA_DIR = "data/xxx"

# ❌ 错误 - __file__ 可能是相对路径，dirname 可能返回空字符串
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "xxx")
```

### 参考正确写法

- `tools/task.py`
- `tools/timer.py`

---

## 2. SPA Fallback 不能拦截 API 路由

**规则：`main.py` 中的 SPA catch-all 路由 `/{full_path:path}` 必须排除 `api/` 开头的路径。**

### 原因

FastAPI/Starlette 的 `{path:path}` 参数会匹配任何路径（包括 `/api/mailbox/player` 这样的 API 路径），与参数化的 API 路由产生冲突，导致 API 请求返回 `index.html` 而不是 JSON。精确匹配路由（如 `/api/npcs`）不受影响，但带路径参数的路由（如 `/api/xxx/{name}`）会被拦截。

### 正确写法

```python
# ✅ 正确 - 排除 API 路径
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"status": "error", "message": "Not found"})
    # ... 正常的 SPA fallback 逻辑

# ❌ 错误 - 会拦截所有参数化的 API 路由
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("index.html")  # /api/mailbox/player 也会走到这里！
```

---

## 3. 前端 Store 的 loading 必须用 finally 恢复

**规则：所有设置 `loading: true` 的异步操作，必须用 `finally` 确保 `loading` 被重置为 `false`。禁止把 `loading: false` 放在 `if (data.status === 'ok')` 的条件分支里。**

### 原因

如果 API 返回了非预期响应（比如被 SPA 返回了 HTML、服务器错误、格式变化等），`loading` 永远不会恢复 → UI 一直转圈。

### 正确写法

```typescript
// ✅ 正确 - finally 保证 loading 一定恢复
fetchData: async () => {
  set({ loading: true });
  try {
    const { data } = await api.getData();
    set({ items: data.items || [] });
  } catch (err) {
    set({ error: '获取失败' });
  } finally {
    set({ loading: false });  // 无论成功失败都执行
  }
},

// ❌ 错误 - status 不是 'ok' 时 loading 永远不恢复
fetchData: async () => {
  set({ loading: true });
  try {
    const { data } = await api.getData();
    if (data.status === 'ok') {
      set({ items: data.items, loading: false });  // 只在 ok 时重置！
    }
    // ← 没有 else，loading 永远是 true
  } catch {
    set({ loading: false });
  }
},
```

---

## 4. 新增功能时的检查清单

添加新的后端模块或前端功能时，**务必检查以下事项**：

- [ ] 后端 Python 文件中的路径是否使用 `Path(__file__).resolve()` 构建？
- [ ] 新增的 GET API 路由如果带路径参数（如 `{name}`），是否会被 SPA fallback 拦截？
- [ ] 前端 Store 中设置 `loading: true` 后，是否在 `finally` 中重置？
- [ ] `.env.production` 中 API 地址是否使用相对路径 `/api`？（前后端同源无需硬编码 IP）

---

## 5. 常见问题排查

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| API 返回 HTML 而不是 JSON | SPA fallback 拦截了 API 路由 | 检查 `/{full_path:path}` 路由 |
| 服务器找不到文件 | 使用了相对路径 | 改用 `Path(__file__).resolve()` |
| UI 一直转圈 | loading 没有恢复 | 使用 `finally` 重置 loading |
| 环境变量不生效 | `.env` 文件路径问题 | 使用绝对路径加载配置 |
