# ChatBot 设计文档

## 1. 项目概述

**ChatBot** 是一个全栈 AI 聊天应用，支持多模型提供商、技能系统、MCP 工具集成、深度思考和 Web 搜索等功能。

| 项目 | 详情 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| AI SDK | OpenAI Python SDK（兼容协议） |
| 前端技术 | 原生 HTML/CSS/JS（SPA 单页应用） |
| 前端依赖 | marked.js（Markdown 渲染）、highlight.js（代码高亮） |
| 通信方式 | SSE (Server-Sent Events) + REST API |
| 数据持久化 | JSON 文件（`data/conversations.json`） |

---

## 2. 目录结构

```
chatbot/
├── backend/
│   ├── main.py              # FastAPI 主应用（608 行）
│   ├── mcp_client.py         # MCP 客户端管理（184 行）
│   ├── skills.json           # 技能/角色定义
│   ├── mcp_config.json       # MCP 服务器配置
│   ├── requirements.txt      # Python 依赖
│   └── data/
│       └── conversations.json # 对话持久化
└── frontend/
    └── index.html             # 前端 SPA（1396 行）
```

---

## 3. 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (SPA)                       │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Sidebar  │  │  Chat Area   │  │  Input Controls       │  │
│  │ 会话列表  │  │  Markdown渲染 │  │  模型/技能/思考/搜索  │  │
│  └──────────┘  └──────────────┘  └──────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │ SSE (stream) + REST (CRUD)
┌───────────────────────▼─────────────────────────────────────┐
│                     Backend (FastAPI)                       │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ REST Routes │  │ AI Streaming │  │   Data Layer      │  │
│  │             │  │              │  │                   │  │
│  │ /api/models │  │ _stream_chat │  │ conversations.json │  │
│  │ /api/skills │  │ _mock_stream │  │                   │  │
│  │ /api/conv/* │  │ DSML Parser  │  │ _load / _save     │  │
│  │ /api/mcp/*  │  │              │  │                   │  │
│  └──────┬──────┘  └──────┬───────┘  └───────────────────┘  │
│         │                │                                  │
│         │    ┌───────────▼────────────┐                     │
│         │    │     Tool Execution     │                     │
│         │    │  ┌──────────────────┐  │                     │
│         │    │  │  Builtin Tools   │  │                     │
│         │    │  │  - web_search    │  │                     │
│         │    │  │    (DuckDuckGo)  │  │                     │
│         │    │  └──────────────────┘  │                     │
│         │    │  ┌──────────────────┐  │                     │
│         │    │  │   MCP Manager    │  │                     │
│         │    │  │  ┌────────────┐  │  │                     │
│         │    │  │  │ MCPServer  │  │  │                     │
│         │    │  │  │ (subprocess)│  │  │                     │
│         │    │  │  └────────────┘  │  │                     │
│         │    │  └──────────────────┘  │                     │
│         │    └────────────────────────┘                     │
└─────────┼───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│                    External Services                         │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐               │
│  │ DeepSeek │  │   Qwen   │  │ MCP Servers  │               │
│  │   API    │  │   API    │  │ (extensible) │               │
│  └──────────┘  └──────────┘  └─────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 核心模块设计

### 4.1 多模型提供者架构（`main.py:38-77`）

支持可扩展的模型提供者注册机制：

```python
PROVIDERS = {
    "deepseek": { "base_url": "...", "api_key_env": "DEEPSEEK_API_KEY", "models": [...] },
    "qwen":     { "base_url": "...", "api_key_env": "DASHSCOPE_API_KEY",  "models": [...] },
}
```

**设计要点：**
- 所有提供者统一通过 OpenAI 兼容 API 调用（`AsyncOpenAI`）
- API Key 从环境变量读取，启动时检测可用性
- 未配置 Key 的模型标记为 `available: false`，前端展示但禁用
- 所有 API Key 均未配置时，自动降级为 **mock 模拟模式**

### 4.2 SSE 流式响应（`main.py:262-357, 538-591`）

使用 SSE（Server-Sent Events）实现 AI 回复的流式传输。

**事件类型：**

| 事件 | 含义 | 方向 |
|------|------|------|
| `thinking_start` | 深度思考开始 | 后端 → 前端 |
| `thinking` | 思考过程内容块 | 后端 → 前端 |
| `thinking_done` | 深度思考结束 | 后端 → 前端 |
| `token` | AI 回答内容块 | 后端 → 前端 |
| `tool_start` | 工具调用开始 | 后端 → 前端 |
| `tool_result` | 工具执行结果 | 后端 → 前端 |
| `tool_done` | 工具调用阶段结束 | 后端 → 前端 |
| `done` | 本轮对话结束 | 后端 → 前端 |

**流式处理流程：**
```
用户消息 → 组装 messages → OpenAI stream API
    ├── reasoning_content 出现 → 发送 thinking 事件
    ├── tool_calls 出现 → 收集并解析
    │   └── 执行工具 → 发送 tool_start/tool_result
    │       └── 工具结果追加到 messages → 递归调用 _stream_chat（无 tools）
    └── content 出现 → 发送 token 事件
```

### 4.3 MCP 客户端（`mcp_client.py`）

实现 MCP (Model Context Protocol) 标准，通过子进程与外部工具服务器通信。

**类结构：**

```
MCPServer
├── connect()          # 启动子进程 → JSON-RPC 握手 → 获取工具列表
├── call_tool()        # JSON-RPC 调用 tools/call
├── close()            # 终止子进程
├── _rpc()             # JSON-RPC 请求/响应，30s 超时
├── _read_loop()       # 子进程 stdout 读取协程
└── _send_notification() # JSON-RPC 通知发送

MCPManager (单例: mcp_manager)
├── connect_server()   # 根据配置创建并连接 MCPServer
├── get_all_tools()    # 返回所有已连接服务器的工具列表
├── call_tool()        # 按名称路由到对应服务器
├── status()           # 连接状态报告
└── close_all()        # 关闭所有连接
```

**JSON-RPC 通信协议（基于 stdin/stdout）：**
```
Subprocess stdin  ← JSON-RPC Request ({"jsonrpc":"2.0","id":N,"method":"...","params":{...}})
Subprocess stdout → JSON-RPC Response ({"jsonrpc":"2.0","id":N,"result":{...}})
```

### 4.4 技能系统（`skills.json`）

通过 `system_prompt` 为不同场景定制 AI 角色和行为：

| 技能 ID | 名称 | 角色定位 |
|---------|------|----------|
| `general` | 通用助手 | 默认通用对话 |
| `coder` | 代码专家 | 软件工程与编程 |
| `writer` | 文案写手 | 内容创作与文案 |
| `analyst` | 数据分析 | 数据驱动分析 |
| `translator` | 翻译官 | 多语言翻译 |
| `teacher` | 导师 | 教学与概念解释 |

**System Prompt 组装优先级（`main.py:504-531`）：**
1. 基础角色设定（`你是 ChatBot，处于「技能名」模式`）
2. Web 搜索指令（如开启）
3. 技能专属 system_prompt
4. 深度思考指令（如开启）
5. 历史消息上下文

### 4.5 DSML 解析器（`main.py:222-257`）

自定义 DSML 格式用于解析模型输出中的工具调用标记。

**语法结构：**
```
<｜tool_calls｜>
  <｜invoke｜ name="web_search">
    <｜parameter｜ name="query">关键词</｜parameter｜>
    <｜parameter｜ name="max_results">5</｜parameter｜>
  </｜invoke｜>
</｜tool_calls｜>
```

使用全角竖线 `｜` (U+FF5C) 代替 `<|>`，避免被模型误认为普通文本分隔符。

### 4.6 内置工具

| 工具 | 实现 | 说明 |
|------|------|------|
| `web_search` | DuckDuckGo (`ddgs.DDGS`) | 通过 DuckDuckGo 搜索引擎获取实时网页信息 |

**工具注册格式**（OpenAI function calling 兼容）：
```python
{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "...",
        "parameters": { "type": "object", "properties": {...}, "required": [...] }
    }
}
```

### 4.7 数据层（`main.py:176-199`）

- **存储格式：** JSON 文件（`data/conversations.json`）
- **数据结构：** `{ id, title, messages[], created_at, updated_at }`
- **消息结构：** `{ role: "user"|"assistant", content, thinking?, tools? }`
- **操作：** CRUD（创建 / 获取 / 删除 / 重命名 / 发送消息）
- **锁策略：** 无并发锁，单用户场景下读-改-写安全

---

## 5. 前端架构（`index.html`）

### 5.1 组成部分

| 组件 | 功能 |
|------|------|
| **Sidebar（侧边栏）** | 会话列表、新建/重命名/删除管理 |
| **Chat Header（头部）** | 当前对话标题、模型标识 |
| **Messages Area（消息区）** | 流式渲染 AI 回复、思考过程、工具结果 |
| **Input Controls（控件栏）** | 模型选择、技能选择、深度思考开关、联网搜索开关 |
| **Input Box（输入框）** | 多行文本输入，Enter 发送，Shift+Enter 换行 |

### 5.2 SSE 事件处理流程

```
fetch POST → ReadableStream → 逐行解析 "data: {...}"
    ├── thinking_start → 创建折叠思考块
    ├── thinking → 流式追加思考内容
    ├── thinking_done → 标记思考完成，创建 answer-body
    ├── token → 流式追加 Markdown 渲染的答案
    ├── tool_start → 创建工具调用卡片（含加载动画）
    ├── tool_result → 替换加载动画为搜索结果/工具结果
    └── done → 刷新对话列表
```

### 5.3 Markdown 渲染链

```
原始内容 → fixMarkdown()（修复格式）→ stripDSML()（移除标记）→ marked.parse() → highlight.js
```

### 5.4 设计风格

- CSS 变量系统驱动（`--accent`、`--bg` 等）
- 手工 CSS 无框架依赖
- 移动端响应式（≤768px 时侧边栏覆盖模式）
- 动画使用 CSS keyframes（淡入、轻点、旋转）

---

## 6. API 接口清单

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 返回前端 HTML |
| `GET` | `/api/models` | 获取模型列表及默认模型 |
| `GET` | `/api/skills` | 获取技能列表 |
| `GET` | `/api/mcp/status` | MCP 连接状态 |
| `GET` | `/api/mcp/tools` | MCP 工具列表 |
| `POST` | `/api/mcp/reload` | 重载 MCP 服务器 |
| `GET` | `/api/conversations` | 获取所有对话（摘要） |
| `POST` | `/api/conversations` | 创建新对话 |
| `GET` | `/api/conversations/{id}` | 获取对话详情 |
| `PUT` | `/api/conversations/{id}` | 重命名对话 |
| `DELETE` | `/api/conversations/{id}` | 删除对话 |
| `POST` | `/api/conversations/{id}/messages` | 发送消息（**SSE 流式响应**） |

---

## 7. 数据流图（一次对话请求）

```
用户输入 → Frontend
    │
    │  POST /api/conversations/{id}/messages
    │  { content, model, thinking, skill, web_search }
    ▼
Backend: send_message()
    │
    ├── 验证对话存在
    ├── 自动生成标题（首条消息）
    ├── 组装 System Prompt:
    │   ├── 角色设定
    │   ├── 搜索指令（可选）
    │   ├── 技能 system_prompt（可选）
    │   └── 思考指令（可选）
    ├── 合并历史上下文 + 用户消息
    ├── 收集工具列表（内置 + MCP）
    │
    ▼
_stream_chat()  ← OpenAI SDK (stream=True)
    │
    ├── [循环] 接收 stream chunk
    │   ├── reasoning_content → 发送 "thinking" SSE 事件
    │   ├── tool_calls delta  → 缓存到 tool_call_buf
    │   └── content delta      → 发送 "token" SSE 事件
    │
    ├── [如果有 tool_calls]
    │   ├── 发送 "tool_start" SSE 事件
    │   ├── 执行工具（builtin 或 MCP）
    │   ├── 发送 "tool_result" SSE 事件
    │   ├── 工具结果追加到 messages
    │   └── 递归调用 _stream_chat()（无 tools）
    │
    └── 发送 "done" SSE 事件
```

---

## 8. 技术决策

| 决策 | 原因 |
|------|------|
| 使用 OpenAI 兼容协议 | 统一 DeepSeek/千问接入方式，减少适配代码 |
| SSE 而非 WebSocket | 单向流（服务端→客户端）即可满足需求，实现更简单 |
| JSON 文件存储 | 轻量级，无需数据库服务（个人实验项目） |
| 原生 HTML/JS 前端 | 无构建工具链，单文件即用，适合快速迭代 |
| 全角竖线 DSML 标记 | `｜` (U+FF5C) 在 LLM 输出中极少出现，避免解析冲突 |
| 递归 _stream_chat | 工具调用后直接流转，无需客户端轮询 |
| 子进程 MCP 通信 | 符合 MCP 标准，进程隔离，支持任意语言编写的工具服务 |
| Mock 降级模式 | 无 API Key 时仍可体验完整 UI 流程 |

---

## 9. 扩展指南

### 9.1 添加新模型提供者

在 `PROVIDERS` 字典中新增条目：

```python
"new_provider": {
    "name": "NewProvider",
    "base_url": "https://api.newprovider.com/v1",
    "api_key_env": "NEWPROVIDER_API_KEY",
    "models": [
        {"id": "model-id", "name": "Model Name"},
    ],
}
```

### 9.2 添加新技能

在 `skills.json` 中添加：

```json
{
    "id": "skill_id",
    "name": "技能名称",
    "icon": "🎯",
    "system_prompt": "你是..."
}
```

### 9.3 添加内置工具

1. 在 `BUILTIN_TOOLS` 列表中注册工具定义
2. 在 `_execute_builtin_tool()` 中添加执行逻辑

### 9.4 添加 MCP 服务器

在 `mcp_config.json` 中添加服务器配置：

```json
{
    "name": "server_name",
    "command": "python",
    "args": ["./mcp_servers/my_server.py"],
    "enabled": true
}
```

---

## 10. 依赖清单

```
fastapi>=0.100.0          # Web 框架
uvicorn[standard]>=0.23.0 # ASGI 服务器
pydantic>=2.0.0           # 数据校验
openai>=1.0.0             # AI API 客户端
```

**运行时动态导入：**
- `ddgs` — DuckDuckGo 搜索（仅在 web_search 触发时 import）

**前端 CDN：**
- `marked.js` 14.1.0 — Markdown 渲染
- `highlight.js` 11.9.0 — 代码语法高亮
