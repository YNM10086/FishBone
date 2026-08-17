"""
小鱼骨项目 — 集中配置管理
所有硬编码常量、路径检测、外部客户端初始化均在此文件
"""
import json
import os
import threading
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

# ── 启动时验证 ArcGIS Pro Python 环境（后台线程执行，绝不阻塞启动） ──
def _verify_arcpy_env() -> str:
    import subprocess as _sp
    try:
        r = _sp.run(
            [ARCGIS_PRO_PYTHON, "-c",
             "import arcpy,sys; "
             "print(sys.executable); "
             "print('Python ' + sys.version.split()[0]); "
             "print('ArcGIS Pro ' + arcpy.GetInstallInfo()['Version'])"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        lines = r.stdout.strip().split("\n")
        py_path = lines[0] if len(lines) > 0 else "未知"
        py_ver = lines[1] if len(lines) > 1 else "未知"
        pro_ver = lines[2] if len(lines) > 2 else "未知"
        return f"ArcGIS: {pro_ver} | Python: {py_ver} | 路径: {py_path}"
    except Exception as e:
        return f"ArcGIS Python 验证失败: {e}"


_ENV_INFO = "ArcGIS Python 环境验证中（后台执行）"


def _verify_arcpy_env_async() -> None:
    """后台线程执行环境验证，完成后更新 _ENV_INFO 并打印"""
    global _ENV_INFO
    _ENV_INFO = _verify_arcpy_env()
    print(f"[启动] {_ENV_INFO}")


threading.Thread(target=_verify_arcpy_env_async, daemon=True).start()

# ── Ollama AI 客户端 ──────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"  # 用 IPv4 而非 localhost，避免 Windows 解析到 IPv6 的空白 Ollama 实例
DEFAULT_OLLAMA_MODEL = "gemma4:latest"

client = OpenAI(
    api_key="ollama",
    base_url=OLLAMA_BASE_URL,
    timeout=30.0
)

# ── DeepSeek API 客户端配置（开发期预置，可在首页修改并持久化） ──────
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_DEEPSEEK_API_KEY = ""

# ── AI 提供者运行时状态（线程安全，支持 local/api 随时切换） ──────────
_ai_lock = threading.Lock()
ai_provider = "local"     # "local" = Ollama | "api" = DeepSeek
ai_local_model = DEFAULT_OLLAMA_MODEL
ai_api_model = DEFAULT_DEEPSEEK_MODEL
ai_api_key = DEFAULT_DEEPSEEK_API_KEY
ai_api_base_url = DEFAULT_DEEPSEEK_BASE_URL

_AI_CONFIG_FILE = os.path.join(PROJECT_ROOT, "ai_config.json")


def _load_ai_config() -> None:
    """启动时从 ai_config.json 恢复用户配置（不存在则用默认值）"""
    global ai_provider, ai_local_model, ai_api_model, ai_api_key, ai_api_base_url
    try:
        with open(_AI_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        with _ai_lock:
            if data.get("provider") in ("local", "api"):
                ai_provider = data["provider"]
            ai_local_model = data.get("local_model") or DEFAULT_OLLAMA_MODEL
            ai_api_model = data.get("api_model") or DEFAULT_DEEPSEEK_MODEL
            ai_api_key = data.get("api_key") or DEFAULT_DEEPSEEK_API_KEY
            ai_api_base_url = data.get("api_base_url") or DEFAULT_DEEPSEEK_BASE_URL
    except (FileNotFoundError, json.JSONDecodeError):
        pass


def save_ai_config() -> None:
    """将当前 AI 配置持久化到 ai_config.json"""
    with _ai_lock:
        data = {
            "provider": ai_provider,
            "local_model": ai_local_model,
            "api_model": ai_api_model,
            "api_key": ai_api_key,
            "api_base_url": ai_api_base_url,
        }
    with open(_AI_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_ai_provider() -> str:
    with _ai_lock:
        return ai_provider


def get_ai_model() -> str:
    """返回当前 provider 正在使用的模型名"""
    with _ai_lock:
        return ai_api_model if ai_provider == "api" else ai_local_model


def get_ai_client() -> OpenAI:
    """根据当前 provider 返回对应的 OpenAI 兼容客户端"""
    with _ai_lock:
        provider = ai_provider
        api_key = ai_api_key
        api_base_url = ai_api_base_url
    if provider == "api":
        return OpenAI(api_key=api_key, base_url=api_base_url, timeout=60.0)
    return client


def set_ai_provider(provider: str) -> str:
    global ai_provider
    with _ai_lock:
        ai_provider = provider if provider == "api" else "local"
        return ai_provider


def set_ai_local_model(model: str) -> None:
    global ai_local_model
    with _ai_lock:
        if model.strip():
            ai_local_model = model.strip()


def set_ai_api_model(model: str) -> None:
    global ai_api_model
    with _ai_lock:
        if model.strip():
            ai_api_model = model.strip()


def set_ai_api_key(key: str) -> None:
    global ai_api_key
    with _ai_lock:
        if key.strip():
            ai_api_key = key.strip()


def set_ai_api_base_url(url: str) -> None:
    global ai_api_base_url
    with _ai_lock:
        if url.strip():
            ai_api_base_url = url.strip().rstrip("/")


def get_ai_config_dict() -> dict:
    with _ai_lock:
        return {
            "provider": ai_provider,
            "local_model": ai_local_model,
            "api_model": ai_api_model,
            "api_key": ai_api_key,
            "api_base_url": ai_api_base_url,
        }

# ── 服务器配置 ────────────────────────────────────────────────────────
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000

# ── 启动信息 ──────────────────────────────────────────────────────────
print(f"[启动] 项目根目录: {PROJECT_ROOT}")
print(f"[启动] {_ENV_INFO}")

_load_ai_config()  # 导入时恢复持久化配置
_provider_name = "本地 Ollama" if ai_provider == "local" else "DeepSeek API"
print(f"[启动] AI 提供者: {_provider_name}  模型: {get_ai_model()}")
print(f"[启动] Ollama: {OLLAMA_BASE_URL}  默认模型: {DEFAULT_OLLAMA_MODEL}")

# ── 天地图服务配置 ─────────────────────────────────────────────────────
TIANDITU_KEY = ""
TIANDITU_GEO_URL = "https://api.tianditu.gov.cn/geocoding"
TIANDITU_SEARCH_URL = "https://api.tianditu.gov.cn/v2/search"
