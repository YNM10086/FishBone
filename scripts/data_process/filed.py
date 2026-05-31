"""
字段编辑工具：对要素类/表的属性字段进行增删改查
用法:
- 模块调用：from filed import run; print(run(feature_class, action, ...))
- 命令行：python filed.py '<json_params>'
"""
import sys
import json
import arcpy
import os
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


_INVALID_FIELD_CHARS = set(r'\/:*?"<>| ')


def _validate_field_name(name: str) -> Optional[str]:
    """校验字段名合法性，返回 None 表示合法，否则返回错误信息"""
    if not name:
        return "字段名不能为空"
    if any(c in _INVALID_FIELD_CHARS for c in name):
        return f"字段名含非法字符（空格/\\/:*?\"<>|）：{name}"
    return None


# ═══════════════════════════════════════════════════════════════════════
# 核心函数
# ═══════════════════════════════════════════════════════════════════════

def run(
    feature_class: str,
    action: str,
    field_name: Optional[str] = None,
    field_type: str = "TEXT",
    field_length: int = 254,
    new_alias: Optional[str] = None,
) -> str:
    try:
        feature_class = _normalize(feature_class)
        action = _safe_strip(action).lower()

        if not feature_class:
            return "ERROR: 参数缺失 feature_class"
        if not action:
            return "ERROR: 参数缺失 action"

        # ── 强制路径校验 ──
        if not arcpy.Exists(feature_class):
            return f"ERROR: 要素类不存在：{feature_class}"

        # ── Schema 锁检测（ArcGIS Pro 打开 GDB 时会阻止外部修改字段） ──
        if not arcpy.TestSchemaLock(feature_class):
            return (
                "ERROR: 无法获取 Schema 锁，请确认：\n"
                "  1. ArcGIS Pro 中已关闭该要素类的属性表\n"
                "  2. 已从地图中移除该图层\n"
                "  3. 已停止所有编辑操作\n"
                "  4. 或完全关闭 ArcGIS Pro 后重试"
            )

        valid_actions = ("list", "add", "delete", "alias")
        if action not in valid_actions:
            return f"ERROR: 不支持的操作 {action}，仅支持 {valid_actions}"

        # ── list：列出所有字段 ──
        if action == "list":
            fields = arcpy.ListFields(feature_class)
            lines = [f"要素类: {feature_class}", f"字段数: {len(fields)}", ""]
            for f in fields:
                lines.append(f"  {f.name} | 类型: {f.type} | 长度: {f.length} | 别名: {f.aliasName}")
            return "SUCCESS:\n" + "\n".join(lines)

        # ── add / delete / alias 需要 field_name ──
        field_name = _safe_strip(field_name) if field_name else ""
        name_err = _validate_field_name(field_name)
        if name_err:
            return f"ERROR: {name_err}"

        if action == "add":
            field_type = _safe_strip(field_type).upper() or "TEXT"
            valid_types = ("TEXT", "FLOAT", "DOUBLE", "SHORT", "LONG", "DATE")
            if field_type not in valid_types:
                return f"ERROR: 字段类型不合法 {field_type}，仅支持 {valid_types}"

            # 去重检查
            existing = [f.name for f in arcpy.ListFields(feature_class)]
            if field_name in existing:
                return f"SUCCESS: 字段已存在，无需添加：{field_name}"

            # 关键修复：仅 TEXT 类型传 field_length
            if field_type == "TEXT":
                arcpy.management.AddField(
                    in_table=feature_class,
                    field_name=field_name,
                    field_type=field_type,
                    field_length=field_length,
                )
            else:
                arcpy.management.AddField(
                    in_table=feature_class,
                    field_name=field_name,
                    field_type=field_type,
                )

            # 二次校验：确认字段真正添加上
            updated = [f.name for f in arcpy.ListFields(feature_class)]
            if field_name in updated:
                return f"SUCCESS: 字段添加成功\n  要素类: {feature_class}\n  字段名: {field_name}\n  类型: {field_type}"
            else:
                return f"ERROR: 操作无报错但字段未生效，请刷新 ArcGIS 或检查缓存：{field_name}"

        elif action == "delete":
            existing = [f.name for f in arcpy.ListFields(feature_class)]
            if field_name not in existing:
                return f"ERROR: 字段不存在，无法删除：{field_name}"

            arcpy.management.DeleteField(
                in_table=feature_class,
                drop_field=field_name,
            )

            updated = [f.name for f in arcpy.ListFields(feature_class)]
            if field_name not in updated:
                return f"SUCCESS: 字段删除成功\n  要素类: {feature_class}\n  字段名: {field_name}"
            else:
                return f"ERROR: 操作无报错但字段未删除，请刷新 ArcGIS：{field_name}"

        elif action == "alias":
            existing = {f.name: f.aliasName for f in arcpy.ListFields(feature_class)}
            if field_name not in existing:
                return f"ERROR: 字段不存在，无法修改别名：{field_name}"

            new_alias = _safe_strip(new_alias) if new_alias else ""
            if not new_alias:
                return "ERROR: alias 操作需要 new_alias 参数"

            arcpy.management.AlterField(
                in_table=feature_class,
                field=field_name,
                new_field_alias=new_alias,
            )

            updated = {f.name: f.aliasName for f in arcpy.ListFields(feature_class)}
            if updated.get(field_name) == new_alias:
                return f"SUCCESS: 字段别名修改成功\n  要素类: {feature_class}\n  字段名: {field_name}\n  新别名: {new_alias}"
            else:
                return f"ERROR: 操作无报错但别名未生效，请刷新 ArcGIS：{field_name}"

    except arcpy.ExecuteError:
        return f"ERROR: ArcPy 执行错误：{arcpy.GetMessages(2)}"
    except Exception as e:
        return f"ERROR: 字段操作失败：{str(e)}（异常类型：{type(e).__name__}）"


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

    result = run(
        feature_class=params.get("feature_class", ""),
        action=params.get("action", ""),
        field_name=params.get("field_name"),
        field_type=params.get("field_type", "TEXT"),
        field_length=params.get("field_length", 254),
        new_alias=params.get("new_alias"),
    )

    if result.startswith("SUCCESS:"):
        _proto_success(result[8:].strip())
    else:
        _proto_error(result[7:].strip())


if __name__ == "__main__":
    main()
