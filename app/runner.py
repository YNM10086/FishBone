"""
小鱼骨项目 — 子进程调度器
协议：优先解析 JSON {"ok": bool, "message"|"error": str}，旧文本格式兜底
"""
import os
import json
import subprocess
from .config import ARCGIS_PRO_PYTHON, PROJECT_ROOT

_COPYRIGHT_NOISE = ("Copyright", "Licensed", "All Rights Reserved", "Authorized Use")


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
                    return data.get("error", "脚本返回未知错误")
        except json.JSONDecodeError:
            pass

    # ── 2. 旧文本格式兜底 ──
    stderr_clean = "\n".join(
        line for line in stderr.split("\n")
        if not any(k in line for k in _COPYRIGHT_NOISE)
    ).strip()

    if result.returncode == 0:
        output = stdout or stderr_clean
        return output if output else "脚本执行完毕，无输出（可能未产生实际效果）"
    else:
        err_detail = stderr_clean or stdout or "(无输出)"
        return f"ArcGIS Pro 执行失败 [{result.returncode}]：{err_detail}"
