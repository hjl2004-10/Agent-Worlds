# 贡献指南

感谢你对 AI_夸父 的关注！以下是参与贡献的方式。

## 提交 Issue

- Bug 报告：描述复现步骤、预期行为、实际行为
- 功能建议：描述使用场景和期望效果
- 在 Issue 中注明标签（bug / feature / question）

## 提交 PR

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m "描述你的更改"`
4. 推送分支：`git push origin feature/your-feature`
5. 创建 Pull Request

## 开发环境

```bash
# 后端
cp config/llm.json.example config/llm.json
# 编辑 llm.json 填入 API Key
pip install -r requirements.txt
python main.py

# 前端
cd static
npm install
npm run dev
```

## 代码规范

项目使用**作用域分层 (Scope-Based Layering)**：

| 层级 | 文件后缀 | 职责 |
|------|----------|------|
| 总控层 | 无后缀 | 配置持有、接口定义、任务分发 |
| 业务层 | `_l1.py` | 个体作用域、流程组装 |
| 原子层 | `_l2.py` | 纯计算、无状态 |

关键原则：

- **严禁越级调用**：总控调业务，业务调原子，不要跨层
- **原子层无状态**：不访问全局变量，纯输入输出
- **新增工具**：在 `tools/` 下注册，参考 [CLAUDE.md](CLAUDE.md) 的工具系统说明
- **新增 Skill**：在 `data/skills/` 下创建文件夹，包含 `skill.hjl` 和 `prompt.md`

## 项目结构

```
api/          # FastAPI 路由
core/         # 核心系统（对话/驱动/记忆/提示词）
tools/        # 工具系统 + Skill + MCP
body/         # NPC 实体定义
env/          # 地图/时间环境
static/src/   # React 前端
data/         # 世界/NPC/Skill 数据
```

## 注意事项

- 不要提交 API Key、密钥等敏感信息
- 不要提交 `workspace/`、`data/runtime/` 等运行时产物
- 提交前确认 `config/` 下的文件是 `.example` 模板，不是真实配置
