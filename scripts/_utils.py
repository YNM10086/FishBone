"""
scripts/ 共享工具 — 独立脚本导入此文件即可，无需任何 sys.path 配置
"""
import os


def normalize(path: str) -> str:
    """路径规范化：去掉引号空格、统一斜杠方向、转绝对路径"""
    if not path:
        return ""
    path = str(path).strip().strip('"').strip("'")
    # 根治 AI 混合斜杠：显式将所有 / 替换为系统分隔符
    if os.name == "nt":
        path = path.replace("/", "\\")
    path = os.path.normpath(path)
    path = os.path.abspath(path)
    if os.name == "nt" and len(path) > 200 and not path.startswith("\\\\?\\"):
        path = f"\\\\?\\{path}"
    return path


def safe_strip(val) -> str:
    """安全去除字符串两端空白"""
    if val is None:
        return ""
    try:
        return str(val).strip()
    except Exception:
        return ""


def safe_upper(val) -> str:
    """安全转大写"""
    return safe_strip(val).upper()
