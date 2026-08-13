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

    try:
        result = subprocess.run(
            [ARCGIS_PRO_PYTHON, script_path, json.dumps(params)],
            capture_output=True, text=True, timeout=120,
            cwd=PROJECT_ROOT,
            encoding="utf-8", errors="replace"
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

    # ── 1. JSON 协议优先 ──
    if stdout:
        try:
            data = json.loads(stdout)
            if isinstance(data, dict) and "ok" in data:
                if data["ok"]:
                    return data.get("message", "")
                else:
                    return _translate_lock_error(data.get("error", "脚本返回未知错误"))
        except json.JSONDecodeError:
            pass

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
