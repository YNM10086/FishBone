"""
小鱼骨项目 — API 路由 + 工作空间状态管理
FastAPI 应用实例在此创建，所有 HTTP 路由在此注册
"""
import os as _os
import threading
import time as _time
from urllib.request import urlopen as _urlopen, Request as _URLRequest
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .ai_engine import process_chat
from .tool_registry import execute_tool
from .templates import render_home_page, render_chat_page
from .chat_store import save_history, load_history, clear_history
from .config import (
    TIANDITU_KEY,
    get_ai_config_dict, set_ai_provider, set_ai_local_model,
    set_ai_api_model, set_ai_api_key, set_ai_api_base_url,
    save_ai_config,
)

# ── FastAPI 应用实例 ──────────────────────────────────────────────────
app = FastAPI(title="小鱼骨GIS助手")

# ── 静态文件挂载 ──────────────────────────────────────────────────────
_STATIC_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "picture")
if _os.path.isdir(_STATIC_DIR):
    app.mount("/picture", StaticFiles(directory=_STATIC_DIR), name="picture")

# ── 请求耗时中间件 ────────────────────────────────────────────────────

@app.middleware("http")
async def _log_request_time(request: Request, call_next):
    start = _time.time()
    response = await call_next(request)
    elapsed = _time.time() - start
    print(f"[接口总耗时] {request.url.path}: {elapsed:.2f}s")
    return response

# ── 工作空间状态（线程安全） ──────────────────────────────────────────
arcgis_workspace = ""
_ws_lock = threading.Lock()


def _get_workspace() -> str:
    with _ws_lock:
        return arcgis_workspace if arcgis_workspace else "未设置"


# ═══════════════════════════════════════════════════════════════════════
# 路由：首页 — 工作目录设置
# ═══════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def home_page():
    return render_home_page(_get_workspace(), get_ai_config_dict())


# ═══════════════════════════════════════════════════════════════════════
# 路由：设置工作目录
# ═══════════════════════════════════════════════════════════════════════

class SetWorkspaceRequest(BaseModel):
    workspace: str


@app.post("/api/set_workspace")
async def set_workspace(request: SetWorkspaceRequest):
    global arcgis_workspace
    with _ws_lock:
        arcgis_workspace = request.workspace.strip().strip('"').strip("'")
    return {
        "status": "success",
        "message": f"工作目录已设置：{arcgis_workspace}",
        "current_workspace": arcgis_workspace
    }


# ═══════════════════════════════════════════════════════════════════════
# 路由：AI 对话
# ═══════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    prompt: str
    history: list = []


@app.post("/api/chat")
def chat(request: ChatRequest):
    workspace = _get_workspace()
    result = process_chat(
        prompt=request.prompt,
        history=request.history,
        workspace=workspace,
        execute_tool_fn=execute_tool
    )
    if "answer" in result:
        updated = request.history + [
            {"role": "user", "content": request.prompt},
            {"role": "assistant", "content": result["answer"]},
        ]
        save_history(updated)
    return result


# ═══════════════════════════════════════════════════════════════════════
# 路由：对话历史持久化
# ═══════════════════════════════════════════════════════════════════════

@app.get("/api/history")
async def get_history():
    return {"history": load_history()}


class ClearHistoryRequest(BaseModel):
    confirm: bool = False


@app.post("/api/history/clear")
async def clear_history_endpoint(_request: ClearHistoryRequest):
    clear_history()
    return {"status": "success", "message": "对话历史已清空"}


# ═══════════════════════════════════════════════════════════════════════
# 路由：瓦片代理（避免浏览器跨域/跟踪拦截）
# ═══════════════════════════════════════════════════════════════════════

@app.get("/api/tile/{z}/{x}/{y}")
async def tile_proxy(z: int, x: int, y: int):
    url = f"https://t0.tianditu.gov.cn/DataServer?T=vec_w&X={x}&Y={y}&L={z}&tk={TIANDITU_KEY}"
    req = _URLRequest(url, headers={"User-Agent": "FishBoneX/1.0"})
    with _urlopen(req, timeout=10) as resp:
        data = resp.read()
    return Response(content=data, media_type=resp.headers.get("Content-Type", "image/png"))


# ═══════════════════════════════════════════════════════════════════════
# 路由：AI 提供者配置（本地 Ollama / DeepSeek API 切换）
# ═══════════════════════════════════════════════════════════════════════

class AIConfigRequest(BaseModel):
    provider: str = "local"       # "local" | "api"
    local_model: str = ""
    api_model: str = ""
    api_key: str = ""
    api_base_url: str = ""


@app.get("/api/ai_config")
async def get_ai_config():
    return get_ai_config_dict()


@app.post("/api/ai_config")
async def set_ai_config(request: AIConfigRequest):
    set_ai_provider(request.provider)
    set_ai_local_model(request.local_model)
    set_ai_api_model(request.api_model)
    set_ai_api_key(request.api_key)
    set_ai_api_base_url(request.api_base_url)
    save_ai_config()
    return {
        "status": "success",
        "message": "AI 配置已保存",
        **get_ai_config_dict(),
    }


# ═══════════════════════════════════════════════════════════════════════
# 路由：聊天页面
# ═══════════════════════════════════════════════════════════════════════

@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    return render_chat_page(_get_workspace(), get_ai_config_dict())
