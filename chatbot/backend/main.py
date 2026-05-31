import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatbot")

app = FastAPI(title="ChatBot API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
CONVERSATIONS_FILE = DATA_DIR / "conversations.json"
FRONTEND_DIR = BASE_DIR.parent / "frontend"
SKILLS_FILE = BASE_DIR / "skills.json"
MCP_CONFIG_FILE = BASE_DIR / "mcp_config.json"

# ── Providers ────────────────────────────────────────────────

PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "models": [
            {"id": "deepseek-v4-pro", "name": "DeepSeek V4 Pro"},
            {"id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash"},
        ],
    },
    "qwen": {
        "name": "千问 (Qwen)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "models": [
            {"id": "qwen-max", "name": "Qwen Max"},
            {"id": "qwen-plus", "name": "Qwen Plus"},
            {"id": "qwen-turbo", "name": "Qwen Turbo"},
        ],
    },
}

ALL_MODELS = []
for pk, pv in PROVIDERS.items():
    api_key = os.getenv(pv["api_key_env"])
    for m in pv["models"]:
        ALL_MODELS.append({
            "id": m["id"],
            "name": m["name"],
            "provider": pk,
            "provider_name": pv["name"],
            "available": bool(api_key),
        })

DEFAULT_MODEL = ALL_MODELS[0]["id"] if ALL_MODELS else "mock"
DEFAULT_SKILL = "general"

# ── Skills ───────────────────────────────────────────────────

def _load_skills():
    if SKILLS_FILE.exists():
        with open(SKILLS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [{"id": "general", "name": "通用助手", "icon": "💬", "system_prompt": ""}]

SKILLS = _load_skills()

# ── MCP ──────────────────────────────────────────────────────

from mcp_client import mcp_manager

MCP_ENABLED = False

BUILTIN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "使用 DuckDuckGo 搜索引擎搜索网页，获取实时、时效性信息。"
                "当你需要最新数据、近期事件或不了解的实时信息时，应调用此工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "返回结果数量，默认 5，最大 10",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
]


async def _execute_builtin_tool(name: str, arguments: dict):
    if name == "web_search":
        from ddgs import DDGS
        query = arguments.get("query", "")
        max_results = min(int(arguments.get("max_results", 5)), 10)
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return {
            "query": query,
            "results": [
                {"title": r["title"], "url": r["href"], "snippet": r["body"]}
                for r in results
            ],
        }
    raise RuntimeError(f"Unknown builtin tool: {name}")


def _load_mcp_config():
    if MCP_CONFIG_FILE.exists():
        with open(MCP_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


async def start_mcp_servers():
    global MCP_ENABLED
    configs = _load_mcp_config()
    for cfg in configs:
        if not cfg.get("enabled", True):
            continue
        try:
            tools = await mcp_manager.connect_server(cfg)
            logger.info(f"MCP [{cfg['name']}] connected, {len(tools)} tools")
            MCP_ENABLED = True
        except Exception as e:
            logger.warning(f"MCP [{cfg['name']}] failed: {e}")


def _resolve_model(model_id: str):
    for m in ALL_MODELS:
        if m["id"] == model_id and m["available"]:
            return m, PROVIDERS[m["provider"]]
    return None, None


def _get_client(provider: dict):
    from openai import AsyncOpenAI
    api_key = os.getenv(provider["api_key_env"])
    return AsyncOpenAI(api_key=api_key, base_url=provider["base_url"])


# ── Data layer ──────────────────────────────────────────────

def _load():
    if CONVERSATIONS_FILE.exists():
        with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save(convs):
    with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(convs, f, ensure_ascii=False, indent=2)


def _find(conv_id: str):
    convs = _load()
    for i, c in enumerate(convs):
        if c["id"] == conv_id:
            return convs, i, c
    raise HTTPException(status_code=404, detail="Conversation not found")


def _gen_title(content: str) -> str:
    return content[:30].replace("\n", " ") + ("..." if len(content) > 30 else "")


def _send_event(evt_type: str, content: str = ""):
    payload = json.dumps({"type": evt_type, "content": content}, ensure_ascii=False)
    return f"data: {payload}\n\n"


# ── Pydantic models ─────────────────────────────────────────

class RenameRequest(BaseModel):
    title: str


class SendMessageRequest(BaseModel):
    content: str
    model: str = DEFAULT_MODEL
    thinking: bool = False
    skill: str = DEFAULT_SKILL


# ── DSML filter ──────────────────────────────────────────────

_DSML_BLOCK_RE = re.compile(
    r'<\uff5ctool_calls\uff5c>.*?</\uff5ctool_calls\uff5c?>',
    re.DOTALL,
)

_DSML_TAG_RE = re.compile(r'</?\uff5c[^>]*\uff5c?>')

_DSML_INVOKE_RE = re.compile(
    r'<\uff5cinvoke\uff5c\s*name="([^"]+)"\s*>(.*?)</\uff5cinvoke\uff5c?>',
    re.DOTALL,
)

_DSML_PARAM_RE = re.compile(
    r'<\uff5cparameter\uff5c\s*name="([^"]+)"[^>]*>(.*?)</\uff5cparameter\uff5c?>',
    re.DOTALL,
)


def _strip_dsml(text: str) -> str:
    text = _DSML_BLOCK_RE.sub("", text)
    return _DSML_TAG_RE.sub("", text).strip(" \t")


def _parse_dsml_tool_calls(text: str) -> list[dict]:
    """Parse DSML function_calls from text, return list of {name, arguments}."""
    calls = []
    for invoke_match in _DSML_INVOKE_RE.finditer(text):
        name = invoke_match.group(1)
        inner = invoke_match.group(2)
        params = {}
        for pm in _DSML_PARAM_RE.finditer(inner):
            params[pm.group(1)] = pm.group(2).strip()
        if name:
            calls.append({"name": name, "arguments": params})
    return calls


# ── AI streaming helpers ────────────────────────────────────

async def _ai_stream(client, model_id: str, messages: list, thinking: bool, tools: list = None):
    kwargs = {"model": model_id, "messages": messages, "stream": True}
    if tools:
        kwargs["tools"] = tools
    stream = await client.chat.completions.create(**kwargs)
    in_thinking = False
    async for chunk in stream:
        delta = chunk.choices[0].delta
        reasoning = getattr(delta, 'reasoning_content', None) or None
        if reasoning:
            if thinking:
                if not in_thinking:
                    in_thinking = True
                    yield ("thinking_start", "")
                yield ("thinking", reasoning)
        elif delta.content:
            content = _strip_dsml(delta.content)
            if not content:
                continue
            if in_thinking:
                in_thinking = False
                yield ("thinking_done", "")
            yield ("content", content)
    if in_thinking:
        yield ("thinking_done", "")


async def _try_tool_calls(client, model_id: str, messages: list, tools: list):
    events = []
    resp = await client.chat.completions.create(
        model=model_id,
        messages=messages,
        tools=tools,
        stream=False,
    )
    choice = resp.choices[0]
    raw_tool_calls = choice.message.tool_calls

    # Fallback: parse DSML from content if no standard tool_calls
    if not raw_tool_calls and choice.message.content:
        dsml_calls = _parse_dsml_tool_calls(choice.message.content)
        if dsml_calls:
            # Build pseudo tool_calls from DSML
            class PseudoTC:
                def __init__(self, idx, name, args):
                    self.id = f"call_{idx}"
                    self.function = type("fn", (), {
                        "name": name,
                        "arguments": json.dumps(args, ensure_ascii=False),
                    })()
            raw_tool_calls = [PseudoTC(i, c["name"], c["arguments"]) for i, c in enumerate(dsml_calls)]

    if not raw_tool_calls:
        return events

    tool_results = []
    for tc in choice.message.tool_calls:
        fn = tc.function
        events.append(("tool_start", json.dumps({"name": fn.name, "args": fn.arguments}, ensure_ascii=False)))
        try:
            args = json.loads(fn.arguments) if fn.arguments else {}
            # Try builtin tools first, then MCP
            builtin_names = [t["function"]["name"] for t in BUILTIN_TOOLS]
            if fn.name in builtin_names:
                result = await _execute_builtin_tool(fn.name, args)
            else:
                result = await mcp_manager.call_tool(fn.name, args)
            result_str = json.dumps(result, ensure_ascii=False)
        except Exception as e:
            result_str = json.dumps({"error": str(e)}, ensure_ascii=False)
        tool_results.append((tc.id, fn.name, result_str))
        events.append(("tool_result", json.dumps({"name": fn.name, "result": result_str}, ensure_ascii=False)))

    messages.append({
        "role": "assistant",
        "tool_calls": [
            {
                "id": tid,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(args, ensure_ascii=False),
                },
            }
            for (tid, name, args) in [
                (t[0], t[1], json.loads(t[2]) if t[2] else {}) for t in tool_results
            ]
        ],
    })
    for tid, name, result_str in tool_results:
        messages.append({"role": "tool", "tool_call_id": tid, "content": result_str})

    events.append(("tool_done", ""))
    return events


async def _mock_stream(user_message: str, model_name: str, thinking: bool, skill_name: str):
    if thinking:
        think_text = (
            f"技能 [{skill_name}] 已激活\n"
            "1. 分析用户意图\n"
            "2. 匹配技能上下文\n"
            "3. 组织回答结构\n"
            "4. 生成回复内容\n\n"
            "> 以上为模拟的深度思考过程"
        )
        yield ("thinking_start", "")
        for ch in think_text:
            yield ("thinking", ch)
            await asyncio.sleep(0.02)
        yield ("thinking_done", "")

    lines = [
        f"当前模式：**模拟回复**\n技能：**{skill_name}** | 模型：{model_name}\n\n",
        "### 功能一览\n\n",
        "| 功能 | 状态 |\n|------|------|\n| 多轮对话 | ✅ |\n| 流式响应 | ✅ |\n| Markdown 渲染 | ✅ |\n| 会话管理 | ✅ |\n",
        "| 多模型切换 | ✅ |\n| 深度思考 | ✅ |\n| 技能系统 | ✅ |\n| MCP 工具 | ✅ |\n\n",
        f"> 💡 收到：**{user_message}**",
    ]
    for line in lines:
        for ch in line:
            yield ("content", ch)
            await asyncio.sleep(0.015)


# ── Routes ──────────────────────────────────────────────────

@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/models")
async def list_models():
    return {"models": ALL_MODELS, "default": DEFAULT_MODEL}


@app.get("/api/skills")
async def list_skills():
    return {"skills": SKILLS, "default": DEFAULT_SKILL}


@app.get("/api/mcp/status")
async def mcp_status():
    mcp_tool_count = len(mcp_manager.get_all_tools())
    return {
        "enabled": MCP_ENABLED or len(BUILTIN_TOOLS) > 0,
        "servers": mcp_manager.status(),
        "tool_count": mcp_tool_count + len(BUILTIN_TOOLS),
        "builtin_count": len(BUILTIN_TOOLS),
    }


@app.get("/api/mcp/tools")
async def mcp_tools():
    return {"tools": mcp_manager.get_all_tools()}


@app.post("/api/mcp/reload")
async def mcp_reload():
    global MCP_ENABLED
    await mcp_manager.close_all()
    MCP_ENABLED = False
    await start_mcp_servers()
    return {"ok": True, "servers": mcp_manager.status()}


@app.get("/api/conversations")
async def list_conversations():
    convs = _load()
    return [
        {
            "id": c["id"],
            "title": c["title"],
            "created_at": c["created_at"],
            "updated_at": c["updated_at"],
            "message_count": len(c["messages"]),
        }
        for c in reversed(convs)
    ]


@app.post("/api/conversations")
async def create_conversation():
    convs = _load()
    now = datetime.now().isoformat()
    conv = {
        "id": uuid.uuid4().hex,
        "title": "新对话",
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }
    convs.append(conv)
    _save(convs)
    return conv


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    _, _, conv = _find(conv_id)
    return conv


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    convs, i, _ = _find(conv_id)
    convs.pop(i)
    _save(convs)
    return {"ok": True}


@app.put("/api/conversations/{conv_id}")
async def rename_conversation(conv_id: str, body: RenameRequest):
    convs, i, conv = _find(conv_id)
    conv["title"] = body.title
    conv["updated_at"] = datetime.now().isoformat()
    _save(convs)
    return conv


@app.post("/api/conversations/{conv_id}/messages")
async def send_message(conv_id: str, body: SendMessageRequest):
    convs, i, conv = _find(conv_id)
    user_content = body.content.strip()

    if not user_content:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if len(conv["messages"]) == 0:
        conv["title"] = _gen_title(user_content)

    skill = next((s for s in SKILLS if s["id"] == body.skill), SKILLS[0])

    ai_messages = []
    ai_messages.append({
        "role": "system",
        "content": (
            f"你是 ChatBot，一个多功能 AI 助手。当前你正处于「{skill['name']}」模式。"
            f"请完全以该角色的身份和风格回答问题。当被问到'你是谁'时，请以当前角色的身份回答。"
        ),
    })
    if BUILTIN_TOOLS:
        ai_messages.append({
            "role": "system",
            "content": (
                "你可以使用 web_search 工具搜索网页获取实时信息。当用户询问需要最新数据、"
                "近期新闻、时效性信息或你不确定的内容时，必须调用 web_search 搜索。\n\n"
                "基于搜索结果回答时，请按以下格式输出：\n"
                "- 每条新闻用「**标题**」加粗作为开头\n"
                "- 如果有时间信息（如发布日期），用 `📅 YYYY-MM-DD` 格式标注在标题后\n"
                "- 每条新闻独立成段，用简明的 1-3 句话概括要点\n"
                "- 使用分隔线 `---` 或编号区分不同条目\n"
                "- 在文末注明数据来源和搜索时间"
            ),
        })
    if skill.get("system_prompt"):
        ai_messages.append({"role": "system", "content": skill["system_prompt"]})
    if body.thinking:
        ai_messages.append({"role": "system", "content": "请先展示推理过程，再给出最终答案。"})

    ai_messages += [{"role": m["role"], "content": m["content"]} for m in conv["messages"]]
    ai_messages.append({"role": "user", "content": user_content})

    model_meta, provider = _resolve_model(body.model)
    use_ai = model_meta is not None
    mcp_tools = BUILTIN_TOOLS + (mcp_manager.get_all_tools() if MCP_ENABLED else [])

    async def generate():
        conv["messages"].append({"role": "user", "content": user_content})
        think_buf = ""
        answer_buf = ""
        tool_entries = []

        try:
            if use_ai:
                client = _get_client(provider)

                # Phase 1: Try tool calling if MCP is available
                if mcp_tools:
                    try:
                        tool_events = await _try_tool_calls(
                            client, body.model, ai_messages, mcp_tools
                        )
                        for evt_type, text in tool_events:
                            if evt_type == "tool_start":
                                yield _send_event("tool_start", text)
                            elif evt_type == "tool_result":
                                tool_entries.append(json.loads(text))
                                yield _send_event("tool_result", text)
                            elif evt_type == "tool_done":
                                yield _send_event("tool_done")
                    except Exception as e:
                        logger.warning(f"Tool call failed: {e}")

                # Phase 2: Stream final answer (without tools if we already called them)
                stream_tools = None if tool_entries else (mcp_tools if mcp_tools else None)
                stream = _ai_stream(client, body.model, ai_messages, body.thinking, stream_tools)
            else:
                stream = _mock_stream(user_content, body.model, body.thinking, skill["name"])

            async for evt_type, text in stream:
                if evt_type in ("thinking_start", "thinking_done"):
                    yield _send_event(evt_type)
                elif evt_type == "thinking":
                    think_buf += text
                    yield _send_event("thinking", text)
                elif evt_type == "content":
                    answer_buf += text
                    yield _send_event("token", text)

        except Exception as e:
            err = f"\n\n> ⚠️ 错误：{str(e)}"
            answer_buf += err
            yield _send_event("token", err)

        msg = {"role": "assistant", "content": answer_buf}
        if think_buf:
            msg["thinking"] = think_buf
        if tool_entries:
            msg["tools"] = tool_entries
        conv["messages"].append(msg)
        conv["updated_at"] = datetime.now().isoformat()
        _save(convs)
        yield _send_event("done")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Entry point ─────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    await start_mcp_servers()


@app.on_event("shutdown")
async def on_shutdown():
    await mcp_manager.close_all()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
