"""
小鱼骨项目 — API 路由 + 工作空间状态管理
FastAPI 应用实例在此创建，所有 HTTP 路由在此注册
"""
import threading
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .ai_engine import process_chat
from .tool_registry import execute_tool
from .templates import render_home_page, render_chat_page

# ── FastAPI 应用实例 ──────────────────────────────────────────────────
app = FastAPI(title="小鱼骨GIS助手")

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
    return render_home_page(_get_workspace())


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
    return process_chat(
        prompt=request.prompt,
        history=request.history,
        workspace=workspace,
        execute_tool_fn=execute_tool
    )


# ═══════════════════════════════════════════════════════════════════════
# 路由：聊天页面
# ═══════════════════════════════════════════════════════════════════════

@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    return render_chat_page(_get_workspace())
