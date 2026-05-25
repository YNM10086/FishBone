"""
小鱼骨项目 — 集中配置管理
所有硬编码常量、路径检测、外部客户端初始化均在此文件
"""
import os
from openai import OpenAI


# ── ArcGIS Pro Python 解释器自动检测 ──────────────────────────────────
def _detect_arcpy_python() -> str:
    candidates = [
        r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe",
        r"D:\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


ARCGIS_PRO_PYTHON = _detect_arcpy_python()
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Ollama AI 客户端 ──────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "qwen2.5:7b"

client = OpenAI(
    api_key="ollama",
    base_url=OLLAMA_BASE_URL,
    timeout=30.0
)

# ── 服务器配置 ────────────────────────────────────────────────────────
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
