"""
要素类创建工具（融合版）
【核心特性】
1. run() 函数可供模块调用 + main() 命令行双模式
2. 父路径为要素数据集时自动继承 Z/M/空间参考，避免面要素创建失败
3. 内置核心工具函数，解耦外部依赖，提升移植性
4. exists_strict() 严格校验，排除 arcpy 缓存误判
用法：
- 模块调用：from create_element import run; print(run(out_path, out_name, ...))
- 命令行：python create_element.py '<json_params>'
"""
import sys
import json
import arcpy
import os
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _protocol import success as _proto_success, error as _proto_error


# ═══════════════════════════════════════════════════════════════════════
# 内置工具函数（解耦外部依赖）
# ═══════════════════════════════════════════════════════════════════════

def _normalize(path: str) -> str:
    """路径归一化：统一正斜杠、去除空白符"""
    if not path:
        return ""
    return os.path.normpath(str(path).strip().strip('"').strip("'")).replace("\\", "/")


def _safe_strip(val: Optional[str]) -> str:
    """安全去空白符，None 返回空字符串"""
    return val.strip() if val and isinstance(val, str) else ""


def _safe_upper(val: Optional[str]) -> str:
    """安全转大写"""
    return val.strip().upper() if val and isinstance(val, str) else ""


def _to_bool(val: Optional[str]) -> Optional[bool]:
    """ENABLED/TRUE/YES/1 → True, DISABLED/FALSE/NO/0 → False, 其余 → None"""
    if val is None:
        return None
    v = _safe_upper(val)
    if v in ("ENABLED", "TRUE", "YES", "1"):
        return True
    if v in ("DISABLED", "FALSE", "NO", "0"):
        return False
    return None


def _exists_strict(path: str) -> bool:
    """严格存在校验：通过 arcpy.Describe 确认 dataType，排除缓存误判"""
    if not path:
        return False
    try:
        desc = arcpy.Describe(path)
        return desc.dataType in ("FeatureClass", "FeatureDataset")
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════
# 核心创建函数
# ═══════════════════════════════════════════════════════════════════════

def run(
    out_path: str,
    out_name: str,
    geometry_type: str = "POINT",
    has_m: Optional[str] = None,
    has_z: Optional[str] = None,
    spatial_reference=4490,
) -> str:
    """在 GDB 或要素数据集中创建点/线/面要素类，返回结果字符串"""
    try:
        # ── 1. 参数清洗与校验 ──
        out_path = _normalize(out_path)
        out_name = _safe_strip(out_name)
        geometry_type = _safe_upper(geometry_type) or "POINT"

        if not out_path or not out_name:
            return f"ERROR: 参数缺失 out_path={out_path!r} out_name={out_name!r}"

        # 防 AI 违规：要素类名禁止带 .shp 后缀
        if out_name.upper().endswith(".SHP") and len(out_name) > 4:
            out_name = out_name[:-4]

        full_path = f"{out_path}/{out_name}"

        if not arcpy.Exists(out_path):
            return f"ERROR: 存放路径不存在：{out_path}"

        valid_types = ["POINT", "POLYLINE", "POLYGON"]
        if geometry_type not in valid_types:
            return f"ERROR: 几何类型不合法 {geometry_type}，仅支持 {valid_types}"

        # ── 2. 自动继承父数据集配置 ──
        is_dataset = False
        sr = None
        has_m_bool = _to_bool(has_m)
        has_z_bool = _to_bool(has_z)

        try:
            desc = arcpy.Describe(out_path)
            is_dataset = desc.dataType == "FeatureDataset"
            if is_dataset:
                # desc.hasZ/hasM 可能返回 bool 或 str，统一转为 bool
                has_z_bool = desc.hasZ in (True, "ENABLED")
                has_m_bool = desc.hasM in (True, "ENABLED")
                sr = desc.spatialReference
        except Exception:
            pass

        # ── 3. 空间参考处理（优先级：父数据集 > 用户指定 > 默认 4490） ──
        if sr is None:
            try:
                if isinstance(spatial_reference, (int, str)):
                    sr = arcpy.SpatialReference(spatial_reference)
                elif isinstance(spatial_reference, arcpy.SpatialReference):
                    sr = spatial_reference
                else:
                    sr = arcpy.SpatialReference(4490)
            except Exception:
                sr = arcpy.SpatialReference(4490)

        # ── 4. 构造参数 ──
        create_kwargs = {
            "out_path": out_path,
            "out_name": out_name,
            "geometry_type": geometry_type,
            "spatial_reference": sr,
            "has_m": "ENABLED" if has_m_bool else "DISABLED",
            "has_z": "ENABLED" if has_z_bool else "DISABLED",
        }

        # ── 5. 去重 ──
        if _exists_strict(full_path):
            return f"SUCCESS: 要素类已存在：{full_path}"

        # ── 6. 创建 ──
        arcpy.management.CreateFeatureclass(**create_kwargs)

        # ── 7. 严格校验 ──
        if _exists_strict(full_path):
            cn = {"POINT": "点", "POLYLINE": "线", "POLYGON": "面"}[geometry_type]
            location = "要素数据集内部" if is_dataset else "GDB 根目录"
            return (
                f"SUCCESS: 要素类创建成功\n"
                f"  名称: {out_name}\n"
                f"  类型: {cn} ({geometry_type})\n"
                f"  创建位置: {location}\n"
                f"  启用 Z 值: {create_kwargs['has_z']}\n"
                f"  启用 M 值: {create_kwargs['has_m']}\n"
                f"  空间参考: {sr.name} (WKID: {sr.factoryCode})\n"
                f"  完整路径: {full_path}"
            )
        else:
            return f"ERROR: 创建后严格检测失败：{full_path}"

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

    out_path = params.get("out_path", "")
    out_name = params.get("out_name", "")
    geometry_type = params.get("geometry_type", "POINT")
    has_m = params.get("has_m")
    has_z = params.get("has_z")
    spatial_reference = params.get("spatial_reference", 4490)

    result = run(out_path, out_name, geometry_type, has_m, has_z, spatial_reference)

    if result.startswith("SUCCESS:"):
        _proto_success(result[8:].strip())   # 去掉 "SUCCESS:" 前缀
    else:
        _proto_error(result[7:].strip())     # 去掉 "ERROR:" 前缀


if __name__ == "__main__":
    main()
