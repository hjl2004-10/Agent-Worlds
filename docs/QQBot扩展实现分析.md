# QQ Bot 扩展实现分析

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      OpenClaw 主程序                         │
│                    (plugin-sdk 接口)                         │
└─────────────────────────┬───────────────────────────────────┘
                          │ registerChannel()
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    QQ Bot Plugin                            │
│  ┌─────────────┬─────────────┬─────────────┬──────────────┐ │
│  │  channel.ts │  gateway.ts │   api.ts    │  outbound.ts │ │
│  │  插件注册   │  WebSocket  │  HTTP API   │   消息发送   │ │
│  └─────────────┴─────────────┴─────────────┴──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ QQ 用户  │    │ QQ 群组  │    │ QQ 频道  │
    │ (C2C)    │    │ (Group)  │    │ (Guild)  │
    └──────────┴    └──────────┴    └──────────┘
```

---

## 二、核心模块解析

### 1. 入口模块 (`index.ts`)

```typescript
const plugin = {
  id: "qqbot",
  name: "QQ Bot",
  register(api: OpenClawPluginApi) {
    setQQBotRuntime(api.runtime);
    api.registerChannel({ plugin: qqbotPlugin });
  },
};
```

**作用**：向 OpenClaw 注册 QQ Bot 通道插件。

---

### 2. 通道插件 (`channel.ts`)

定义了 QQ Bot 的完整能力：

| 能力 | 说明 |
|------|------|
| `capabilities` | 支持私聊+群聊、媒体消息、不支持 Reaction |
| `messaging` | 消息目标解析（c2c:xxx, group:xxx 格式）|
| `config` | 账户配置管理（AppID、Secret、权限控制）|
| `outbound` | 消息发送（文本分块、限流）|
| `gateway` | WebSocket 连接管理 |
| `status` | 运行状态追踪 |

---

### 3. WebSocket 网关 (`gateway.ts`)

**核心职责**：

```
1. 连接 QQ Bot WebSocket 网关
2. 鉴权 (Identify) + 心跳维护
3. 接收消息事件 (C2C_MESSAGE_CREATE, GROUP_AT_MESSAGE_CREATE 等)
4. 消息队列 + 异步处理（防止阻塞心跳）
5. 断线重连 + Session 恢复
6. 权限级别降级（群聊→频道）
```

**关键流程**：

```
WebSocket 连接
    │
    ▼
收到 Hello (op=10)
    │
    ├── 有 session_id → 发送 Resume (op=6)
    │
    └── 无 session   → 发送 Identify (op=2)
                          │
                          ▼
                    收到 READY (t=READY)
                          │
                          ▼
                    开始心跳循环
                          │
                          ▼
                    接收消息事件 → 入队 → 异步处理
```

**消息处理流程**：

```
收到消息
    │
    ▼
下载附件（图片/语音）到本地
    │
    ▼
构建系统提示词（用户信息、定时提醒能力、图片发送能力）
    │
    ▼
调用 OpenClaw Runtime 的 dispatchReply
    │
    ▼
AI 生成回复
    │
    ▼
解析回复内容（检测 <qqimg> 标签、QQBOT_PAYLOAD）
    │
    ▼
发送文本/图片/富媒体消息
```

---

### 4. HTTP API (`api.ts`)

**核心功能**：

| 函数 | 作用 |
|------|------|
| `getAccessToken()` | 获取/缓存 Access Token |
| `getGatewayUrl()` | 获取 WebSocket 网关地址 |
| `sendC2CMessage()` | 发送私聊消息 |
| `sendGroupMessage()` | 发送群聊消息 |
| `sendProactiveC2CMessage()` | 主动发送私聊（无需 msg_id）|
| `uploadC2CMedia()` | 上传富媒体文件 |
| `sendC2CImageMessage()` | 发送图片消息 |
| `startBackgroundTokenRefresh()` | 后台自动刷新 Token |

**API 端点**：

```
Token:     https://bots.qq.com/app/getAppAccessToken
Gateway:   https://api.sgroup.qq.com/gateway
发消息:    https://api.sgroup.qq.com/v2/users/{openid}/messages
发群消息:  https://api.sgroup.qq.com/v2/groups/{group_openid}/messages
上传文件:  https://api.sgroup.qq.com/v2/users/{openid}/files
```

---

### 5. 主动消息 (`proactive.ts`)

**用途**：定时任务触发的消息推送。

```typescript
interface ProactiveSendOptions {
  to: string;        // 目标 openid
  text: string;      // 消息内容
  type?: "c2c" | "group";
  imageUrl?: string;
}
```

**限制**：主动消息每月每用户限 4 条。

---

### 6. 消息发送 (`outbound.ts`)

**限流机制**：

- 同一 message_id 1 小时内最多回复 4 次
- 超过限制需降级为主动消息

---

## 三、关键特性

### 1. 权限级别降级

```typescript
const INTENT_LEVELS = [
  { name: "full",          intents: 频道+私信+群聊 },  // 需要申请
  { name: "group+channel", intents: 频道+群聊 },
  { name: "channel-only",  intents: 仅频道 },          // 默认权限
];
```

如果高权限连接失败，自动降级到低权限重试。

### 2. Session 持久化

断线重连时，保存/恢复 session_id 和 last_seq，实现 Resume：

```typescript
interface SessionState {
  sessionId: string;
  lastSeq: number | null;
  intentLevelIndex: number;
  accountId: string;
}
```

### 3. 消息队列

防止消息处理阻塞心跳：

```typescript
const MESSAGE_QUEUE_SIZE = 1000;
// 消息入队 → 独立的处理循环 → 异步处理
```

### 4. 图片发送支持

三种方式：

1. **`<qqimg>路径</qqimg>` 标签**：AI 输出，自动解析发送
2. **QQBOT_PAYLOAD JSON**：结构化载荷，支持本地文件
3. **Markdown 格式**：`![](url)`，仅支持公网 URL

### 5. 语音消息处理

QQ 语音使用 SILK 编码，需要转换为 WAV：

```typescript
convertSilkToWav(localPath, downloadDir);
```

---

## 四、单独开发 QQ Bot 的步骤

### 方案 A：从零开发（独立应用）

#### 1. 准备工作

```bash
# 1. 在 QQ 开放平台创建机器人
# https://q.qq.com/

# 2. 获取 AppID 和 ClientSecret

# 3. 配置沙箱（添加测试用户）
```

#### 2. 核心代码结构

```
my-qqbot/
├── src/
│   ├── index.ts          # 入口
│   ├── gateway.ts        # WebSocket 连接
│   ├── api.ts            # HTTP API 封装
│   ├── message.ts        # 消息处理
│   └── types.ts          # 类型定义
├── package.json
└── tsconfig.json
```

#### 3. 核心实现要点

**步骤 1：获取 Access Token**

```typescript
async function getAccessToken(appId: string, clientSecret: string) {
  const res = await fetch("https://bots.qq.com/app/getAppAccessToken", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ appId, clientSecret }),
  });
  const data = await res.json();
  return data.access_token; // 有效期约 7200 秒
}
```

**步骤 2：连接 WebSocket**

```typescript
async function connectGateway(accessToken: string) {
  // 获取网关地址
  const gatewayRes = await fetch("https://api.sgroup.qq.com/gateway", {
    headers: { Authorization: `QQBot ${accessToken}` },
  });
  const { url } = await gatewayRes.json();

  // 建立 WebSocket
  const ws = new WebSocket(url);

  ws.on("message", (data) => {
    const payload = JSON.parse(data);

    if (payload.op === 10) {
      // Hello: 发送 Identify
      ws.send(JSON.stringify({
        op: 2,
        d: {
          token: `QQBot ${accessToken}`,
          intents: 1 << 25 | 1 << 30, // GROUP_AND_C2C | PUBLIC_GUILD_MESSAGES
          shard: [0, 1],
        },
      }));

      // 启动心跳
      setInterval(() => {
        ws.send(JSON.stringify({ op: 1, d: null }));
      }, payload.d.heartbeat_interval);
    }

    if (payload.t === "C2C_MESSAGE_CREATE") {
      // 收到私聊消息
      handleMessage(payload.d);
    }

    if (payload.t === "GROUP_AT_MESSAGE_CREATE") {
      // 收到群聊 @ 消息
      handleGroupMessage(payload.d);
    }
  });
}
```

**步骤 3：发送消息**

```typescript
async function sendMessage(accessToken: string, openid: string, content: string, msgId?: string) {
  await fetch(`https://api.sgroup.qq.com/v2/users/${openid}/messages`, {
    method: "POST",
    headers: {
      Authorization: `QQBot ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      content,
      msg_type: 0,
      msg_id: msgId, // 被动回复需要
    }),
  });
}
```

**步骤 4：对接 AI**

```typescript
async function handleMessage(event: C2CMessageEvent) {
  const userMessage = event.content;

  // 调用 AI API
  const aiResponse = await callAI(userMessage);

  // 发送回复
  await sendMessage(accessToken, event.author.user_openid, aiResponse, event.id);
}
```

#### 4. 完整最小示例

```typescript
import WebSocket from "ws";

const APP_ID = "你的AppID";
const CLIENT_SECRET = "你的ClientSecret";

let accessToken = "";
let ws: WebSocket;

async function main() {
  // 1. 获取 Token
  const tokenRes = await fetch("https://bots.qq.com/app/getAppAccessToken", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ appId: APP_ID, clientSecret: CLIENT_SECRET }),
  });
  accessToken = (await tokenRes.json()).access_token;

  // 2. 获取 Gateway URL
  const gwRes = await fetch("https://api.sgroup.qq.com/gateway", {
    headers: { Authorization: `QQBot ${accessToken}` },
  });
  const gatewayUrl = (await gwRes.json()).url;

  // 3. 连接 WebSocket
  ws = new WebSocket(gatewayUrl);

  ws.on("message", async (data) => {
    const payload = JSON.parse(data.toString());

    if (payload.op === 10) {
      // Identify
      ws.send(JSON.stringify({
        op: 2,
        d: {
          token: `QQBot ${accessToken}`,
          intents: 1 << 25, // GROUP_AND_C2C
          shard: [0, 1],
        },
      }));

      // 心跳
      setInterval(() => ws.send(JSON.stringify({ op: 1, d: null })), payload.d.heartbeat_interval);
    }

    if (payload.t === "C2C_MESSAGE_CREATE") {
      console.log("收到消息:", payload.d.content);
      await reply(payload.d.author.user_openid, "收到！", payload.d.id);
    }
  });
}

async function reply(openid: string, content: string, msgId: string) {
  await fetch(`https://api.sgroup.qq.com/v2/users/${openid}/messages`, {
    method: "POST",
    headers: {
      Authorization: `QQBot ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content, msg_type: 0, msg_id: msgId }),
  });
}

main();
```

---

### 方案 B：基于 OpenClaw SDK 开发（推荐）

如果你想复用 OpenClaw 的框架能力：

```typescript
import { ChannelPlugin } from "openclaw/plugin-sdk";

const myQQBotPlugin: ChannelPlugin = {
  id: "my-qqbot",
  capabilities: { chatTypes: ["direct", "group"], media: true },
  gateway: { startAccount: async (ctx) => { /* 你的网关逻辑 */ } },
  outbound: {
    sendText: async ({ to, text }) => { /* 你的发送逻辑 */ },
  },
};
```

---

## 五、关键注意事项

| 问题 | 解决方案 |
|------|----------|
| Token 过期 | 提前 5 分钟后台刷新 |
| 连接断开 | 指数退避重连 + Session Resume |
| 权限不足 | 自动降级 intents |
| 消息处理阻塞 | 消息队列 + 异步处理 |
| 1小时回复限制 | 降级为主动消息（每月4条）|
| 图片发送 | 本地文件转 Base64，URL 直接发 |
| 语音消息 | SILK → WAV 转码 |

---

## 六、总结

OpenClaw 的 QQ Bot 扩展是一个**生产级实现**，包含：

1. **完整的 WebSocket 生命周期管理**
2. **消息队列 + 异步处理**
3. **断线重连 + Session 恢复**
4. **权限降级机制**
5. **富媒体支持（图片、语音）**
6. **与 AI 模型的深度集成**

单独开发时，核心是理解 **QQ Bot API 的 WebSocket 协议** 和 **HTTP API 规范**，然后对接你选择的 AI 服务。

---

*文档生成时间：2026-02-20*
