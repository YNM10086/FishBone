"""
独立脚本：删除用户指定的文件/文件夹/GDB内部对象
用法: python delete_file.py '<json_params>'
自动识别路径类型：含 .gdb/ 走 arcpy.Delete，否则走 os.remove/shutil.rmtree
"""
import sys
import json
import arcpy
import os
import shutil
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _protocol import success as _proto_success, error as _proto_error


# ═══════════════════════════════════════════════════════════════════════
# 内置工具函数
# ═══════════════════════════════════════════════════════════════════════

def _normalize(path: str) -> str:
    if not path:
        return ""
    return os.path.normpath(str(path).strip().strip('"').strip("'")).replace("\\", "/")


def _safe_strip(val: Optional[str]) -> str:
    return val.strip() if val and isinstance(val, str) else ""


def _is_gdb_internal(path: str) -> bool:
    """判断路径是否指向 GDB 内部对象（要素类/数据集等）"""
    return ".gdb/" in path.replace("\\", "/").lower()


# ═══════════════════════════════════════════════════════════════════════
# 核心函数
# ═══════════════════════════════════════════════════════════════════════

def run(target_path: str) -> str:
    try:
        target_path = _normalize(target_path)
        if not target_path:
            return "ERROR: target_path 为必填"

        is_gdb_obj = _is_gdb_internal(target_path)

        # ── GDB 内部对象：走 arcpy ──
        if is_gdb_obj:
            if not arcpy.Exists(target_path):
                return f"ERROR: 对象不存在：{target_path}"
            try:
                arcpy.management.Delete(target_path)
            except arcpy.ExecuteError:
                return f"ERROR: ArcPy 执行错误：{arcpy.GetMessages(2)}"
            if not arcpy.Exists(target_path):
                return f"SUCCESS: 对象删除成功：{target_path}"
            else:
                return f"ERROR: 操作无报错但对象仍然存在：{target_path}"

        # ── 普通文件/文件夹：走 OS ──
        if not os.path.exists(target_path):
            return f"ERROR: 路径不存在：{target_path}"

        if os.path.isfile(target_path):
            os.remove(target_path)
            kind = "文件"
        elif os.path.isdir(target_path):
            shutil.rmtree(target_path)
            kind = "文件夹"
        else:
            return f"ERROR: 无法识别的路径类型：{target_path}"

        if not os.path.exists(target_path):
            return f"SUCCESS: {kind}删除成功：{target_path}"
        else:
            return f"ERROR: 删除后校验失败，{kind}可能未被完全删除：{target_path}"

    except PermissionError:
        return f"ERROR: 权限不足，无法删除：{target_path}"
    except arcpy.ExecuteError:
        return f"ERROR: ArcPy 执行错误：{arcpy.GetMessages(2)}"
    except Exception as e:
        return f"ERROR: 删除失败：{str(e)}（异常类型：{type(e).__name__}）"


# ═══════════════════════════════════════════════════════════════════════
# 命令行入口
# ═══════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        _proto_error("缺少参数：请传入 JSON 格式的参数字符串")
        return
    try:
        params = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        _proto_error("参数格式错误：请传入合法的 JSON 字符串")
        return

    target_path = params.get("target_path", "")
    result = run(target_path)

    if result.startswith("SUCCESS:"):
        _proto_success(result[8:].strip())
    else:
        _proto_error(result[7:].strip())


if __name__ == "__main__":
    main()
