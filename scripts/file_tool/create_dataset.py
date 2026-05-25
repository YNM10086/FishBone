"""
要素数据集创建工具（与 create_element.py 共享内置工具函数）
【核心特性】
1. run() 函数可供模块调用 + main() 命令行双模式
2. 内置归一化函数，与 create_element 的路径/名称处理完全一致
3. 空间参考容错：非法 WKID 自动降级为 4490
用法：
- 模块调用：from create_dataset import run; print(run(gdb_path, dataset_name, ...))
- 命令行：python create_dataset.py '<json_params>'
"""
import sys
import json
import arcpy
import os
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _protocol import success as _proto_success, error as _proto_error


# ═══════════════════════════════════════════════════════════════════════
# 内置工具函数（与 create_element.py 完全一致）
# ═══════════════════════════════════════════════════════════════════════

def _normalize(path: str) -> str:
    """路径归一化：统一正斜杠、去除空白符"""
    if not path:
        return ""
    return os.path.normpath(str(path).strip().strip('"').strip("'")).replace("\\", "/")


def _safe_strip(val: Optional[str]) -> str:
    """安全去空白符，None 返回空字符串"""
    return val.strip() if val and isinstance(val, str) else ""


# ═══════════════════════════════════════════════════════════════════════
# 核心创建函数
# ═══════════════════════════════════════════════════════════════════════

def run(
    gdb_path: str,
    dataset_name: str,
    spatial_reference=4490,
) -> str:
    """在 GDB 中创建要素数据集，返回结果字符串"""
    try:
        # ── 1. 参数清洗 ──
        gdb_path = _normalize(gdb_path)
        dataset_name = _safe_strip(dataset_name)
        full_path = f"{gdb_path}/{dataset_name}"

        if not gdb_path or not dataset_name:
            return f"ERROR: 参数缺失 gdb_path={gdb_path!r} dataset_name={dataset_name!r}"

        # ── 2. 前置校验 ──
        if not arcpy.Exists(gdb_path):
            return f"ERROR: GDB 不存在：{gdb_path}\n请先确认数据库路径正确或先创建 GDB"

        arcpy.env.workspace = gdb_path

        if arcpy.Exists(full_path):
            return f"SUCCESS: 要素数据集已存在：{full_path}"

        # ── 3. 空间参考（容错降级，与 create_element 一致） ──
        try:
            if isinstance(spatial_reference, (int, str)):
                sr = arcpy.SpatialReference(spatial_reference)
            elif isinstance(spatial_reference, arcpy.SpatialReference):
                sr = spatial_reference
            else:
                sr = arcpy.SpatialReference(4490)
        except Exception:
            sr = arcpy.SpatialReference(4490)

        # ── 4. 创建 ──
        arcpy.management.CreateFeatureDataset(
            out_dataset_path=gdb_path,
            out_name=dataset_name,
            spatial_reference=sr,
        )

        # ── 5. 严格校验 ──
        if arcpy.Exists(full_path):
            return (
                f"SUCCESS: 要素数据集创建成功\n"
                f"  名称: {dataset_name}\n"
                f"  数据集完整路径: {full_path}\n"
                f"  所在 GDB: {gdb_path}\n"
                f"  坐标: {sr.name} (WKID: {sr.factoryCode})"
            )
        else:
            return f"ERROR: 创建后检测失败 {full_path}"

    except arcpy.ExecuteError:
        return f"ERROR: ArcPy 执行错误：{arcpy.GetMessages(2)}"
    except Exception as e:
        return f"ERROR: 创建失败：{str(e)}（异常类型：{type(e).__name__}）"


# ═══════════════════════════════════════════════════════════════════════
# 命令行入口
# ═══════════════════════════════════════════════════════════════════════

def main():
    """命令行入口：接收 JSON 参数，输出 JSON 协议结果"""
    if len(sys.argv) < 2:
        _proto_error("缺少参数：请传入 JSON 格式的参数字符串")
        return

    try:
        params = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        _proto_error("参数格式错误：请传入合法的 JSON 字符串")
        return

    gdb_path = params.get("gdb_path", "")
    dataset_name = params.get("dataset_name", "")
    spatial_reference = params.get("spatial_reference", 4490)

    result = run(gdb_path, dataset_name, spatial_reference)

    if result.startswith("SUCCESS:"):
        _proto_success(result[8:].strip())
    else:
        _proto_error(result[7:].strip())


if __name__ == "__main__":
    main()
