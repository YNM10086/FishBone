"""
小鱼骨项目 — 子进程调度器
协议：优先解析 JSON {"ok": bool, "message"|"error": str}，旧文本格式兜底
"""
import os
import json
import subprocess
from .config import ARCGIS_PRO_PYTHON, PROJECT_ROOT

_COPYRIGHT_NOISE = ("Copyright", "Licensed", "All Rights Reserved", "Authorized Use")

# ── ArcGIS schema lock 冲突错误识别（兜底：前置检测漏网时的最后防线） ──
_LOCK_ERROR_MARKS = ("000464", "schema lock", "cannot acquire")


def _extract_protocol_json(stdout: str) -> dict | None:
    """从子进程 stdout 中提取协议 JSON：逐行倒序扫描，取最后一个含 ok 键的 JSON"""
    if not stdout:
        return None
    lines = stdout.split("\n")
    for line in reversed(lines):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
            if isinstance(data, dict) and "ok" in data:
                return data
        except (json.JSONDecodeError, Exception):
            continue
    return None


def _translate_lock_error(text: str) -> str:
    """识别 ArcGIS schema lock 冲突错误，翻译为明确的操作被占用提示"""
    if not text:
        return text
    low = text.lower()
    if any(mark in low for mark in _LOCK_ERROR_MARKS):
        return (
            "数据库锁冲突：ArcGIS 正在占用目标数据（schema lock），"
            "请关闭 ArcGIS 工程后再执行编辑操作。"
            f"\n原始错误：{text[:200]}"
        )
    return text


def call_script(script_name: str, params: dict) -> str:
    """通过 ArcGIS Pro Python 执行 scripts/<script_name>.py，返回结果文本"""
    script_path = os.path.join(PROJECT_ROOT, "scripts", f"{script_name}.py")

    # 强制子进程 UTF-8 输出：ArcGIS Pro Python 默认按系统 ANSI 编码(cp936)写管道，
    # 若按 utf-8 读取会导致全部中文结果乱码（2026-08-17 修复）
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    try:
        result = subprocess.run(
            [ARCGIS_PRO_PYTHON, script_path, json.dumps(params)],
            capture_output=True, text=True, timeout=120,
            cwd=PROJECT_ROOT,
            encoding="utf-8", errors="replace",
            env=env,
        )
    except FileNotFoundError:
        return (
            f"ArcGIS Pro Python 解释器未找到：{ARCGIS_PRO_PYTHON}\n"
            "请确认 ArcGIS Pro 已安装且路径正确"
        )
    except subprocess.TimeoutExpired:
        return "ArcGIS Pro 执行超时（>120s）"

    stdout = result.stdout.strip() if result.stdout else ""
    stderr = result.stderr.strip() if result.stderr else ""

    # ── 1. JSON 协议优先（容错） ──
    # 部分 arcpy 工具（如 SplitByAttributes）的底层 C++ 会把进度行直接写到 stdout，
    # 混在协议 JSON 前后，故逐行扫描：取最后一个可解析且含 ok 键的 JSON 行
    protocol = _extract_protocol_json(stdout)
    if protocol is not None:
        if protocol["ok"]:
            return protocol.get("message", "")
        else:
            return _translate_lock_error(protocol.get("error", "脚本返回未知错误"))

    # ── 2. 旧文本格式兜底 ──
    stderr_clean = "\n".join(
        line for line in stderr.split("\n")
        if not any(k in line for k in _COPYRIGHT_NOISE)
    ).strip()

    if result.returncode == 0:
        output = stdout or stderr_clean
        return _translate_lock_error(output) if output else "脚本执行完毕，无输出（可能未产生实际效果）"
    else:
        err_detail = stderr_clean or stdout or "(无输出)"
        return _translate_lock_error(f"ArcGIS Pro 执行失败 [{result.returncode}]：{err_detail}")
