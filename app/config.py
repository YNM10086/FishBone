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

# ── 启动时验证 ArcGIS Pro Python 环境 ─────────────────────────────────
def _verify_arcpy_env() -> str:
    import subprocess as _sp
    try:
        r = _sp.run(
            [ARCGIS_PRO_PYTHON, "-c",
             "import arcpy,sys; "
             "print(sys.executable); "
             "print('Python ' + sys.version.split()[0]); "
             "print('ArcGIS Pro ' + arcpy.GetInstallInfo()['Version'])"],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace",
        )
        lines = r.stdout.strip().split("\n")
        py_path = lines[0] if len(lines) > 0 else "未知"
        py_ver = lines[1] if len(lines) > 1 else "未知"
        pro_ver = lines[2] if len(lines) > 2 else "未知"
        return f"ArcGIS: {pro_ver} | Python: {py_ver} | 路径: {py_path}"
    except Exception as e:
        return f"ArcGIS Python 验证失败: {e}"

_ENV_INFO = _verify_arcpy_env()  # 导入时执行一次

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

# ── 启动信息 ──────────────────────────────────────────────────────────
print(f"[启动] 项目根目录: {PROJECT_ROOT}")
print(f"[启动] {_ENV_INFO}")
print(f"[启动] Ollama: {OLLAMA_BASE_URL}  模型: {OLLAMA_MODEL}")
