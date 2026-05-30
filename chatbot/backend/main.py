import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="ChatBot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CONVERSATIONS_FILE = DATA_DIR / "conversations.json"

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

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

# ── Build flat model list ────────────────────────────────────

ALL_MODELS = []
for provider_key, provider in PROVIDERS.items():
    api_key = os.getenv(provider["api_key_env"])
    for m in provider["models"]:
        ALL_MODELS.append({
            "id": m["id"],
            "name": m["name"],
            "provider": provider_key,
            "provider_name": provider["name"],
            "available": bool(api_key),
        })

DEFAULT_MODEL = ALL_MODELS[0]["id"] if ALL_MODELS else "mock"

# ── Resolve model → provider & client ────────────────────────

def _resolve_model(model_id: str):
    for m in ALL_MODELS:
        if m["id"] == model_id and m["available"]:
            provider = PROVIDERS[m["provider"]]
            return m, provider
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


# ── Pydantic models ─────────────────────────────────────────

class RenameRequest(BaseModel):
    title: str


class SendMessageRequest(BaseModel):
    content: str
    model: str = DEFAULT_MODEL


# ── AI streaming ────────────────────────────────────────────

async def _ai_stream(client, model_id: str, messages: list):
    stream = await client.chat.completions.create(
        model=model_id,
        messages=messages,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


async def _mock_stream(user_message: str, model_name: str):
    available = [m for m in ALL_MODELS if m["available"]]
    avail_hint = ""
    if available:
        names = "、".join(m["name"] for m in available)
        avail_hint = f"已检测到可用模型：{names}，请选择后即可使用。\n\n"
    else:
        avail_hint = (
            "设置 `DEEPSEEK_API_KEY` 或 `DASHSCOPE_API_KEY` 环境变量即可接入 AI。\n\n"
        )

    lines = [
        f"当前模式：**模拟回复** (模型: {model_name})\n\n",
        avail_hint,
        "### Markdown 功能演示\n\n",
        "- 无序列表项\n",
        "- 另一个列表项\n",
        "  - 嵌套列表\n",
        "\n",
        "1. 有序列表\n",
        "2. 第二项\n",
        "\n",
        "```python\nimport json\ndata = {\"hello\": \"world\"}\nprint(json.dumps(data, indent=2))\n```\n\n",
        "| 功能 | 状态 |\n|------|------|\n| 多轮对话 | ✅ |\n| 流式响应 | ✅ |\n| Markdown 渲染 | ✅ |\n| 会话管理 | ✅ |\n| 多模型切换 | ✅ |\n\n",
        f"> 💡 收到你的消息：**{user_message}**",
    ]
    for line in lines:
        for ch in line:
            yield ch
            await asyncio.sleep(0.015)


# ── Static files ────────────────────────────────────────────

@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")


# ── Models API ───────────────────────────────────────────────

@app.get("/api/models")
async def list_models():
    return {
        "models": ALL_MODELS,
        "default": DEFAULT_MODEL,
    }


# ── Conversations API ───────────────────────────────────────

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

    ai_messages = [{"role": m["role"], "content": m["content"]} for m in conv["messages"]]
    ai_messages.append({"role": "user", "content": user_content})

    model_meta, provider = _resolve_model(body.model)
    use_ai = model_meta is not None

    async def generate():
        conv["messages"].append({"role": "user", "content": user_content})
        full = ""

        try:
            if use_ai:
                client = _get_client(provider)
                stream = _ai_stream(client, body.model, ai_messages)
            else:
                stream = _mock_stream(user_content, body.model)

            async for token in stream:
                full += token
                payload = json.dumps({"type": "token", "content": token}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

        except Exception as e:
            err = f"\n\n> ⚠️ 错误：{str(e)}"
            full += err
            yield f"data: {json.dumps({'type': 'token', 'content': err}, ensure_ascii=False)}\n\n"

        conv["messages"].append({"role": "assistant", "content": full})
        conv["updated_at"] = datetime.now().isoformat()
        _save(convs)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
