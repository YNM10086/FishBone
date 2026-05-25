"""
字段编辑工具：对要素类/表的属性字段进行增删改查
用法:
- 模块调用：from filed import run; print(run(feature_class, action, ...))
- 命令行：python filed.py '<json_params>'
支持操作：list(查) / add(增) / delete(删) / alias(改别名)
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
    """
    对要素类执行字段操作，返回结果字符串

    action:
      list   — 列出所有字段
      add    — 添加字段 (需 field_name, 可选 field_type/field_length)
      delete — 删除字段 (需 field_name)
      alias  — 修改字段别名 (需 field_name, new_alias)
    """
    try:
        feature_class = _normalize(feature_class)
        action = _safe_strip(action).lower()

        if not feature_class:
            return "ERROR: 参数缺失 feature_class 为必填"
        if not action:
            return "ERROR: 参数缺失 action 为必填"

        if not arcpy.Exists(feature_class):
            return f"ERROR: 要素类不存在：{feature_class}"

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
        if not field_name:
            return "ERROR: 此操作需要 field_name 参数"

        if action == "add":
            valid_types = ("TEXT", "FLOAT", "DOUBLE", "SHORT", "LONG", "DATE")
            field_type = _safe_strip(field_type).upper() or "TEXT"
            if field_type not in valid_types:
                return f"ERROR: 字段类型不合法 {field_type}，仅支持 {valid_types}"

            arcpy.management.AddField(
                in_table=feature_class,
                field_name=field_name,
                field_type=field_type,
                field_length=field_length,
            )
            return f"SUCCESS: 字段添加成功\n  要素类: {feature_class}\n  字段名: {field_name}\n  类型: {field_type}\n  长度: {field_length}"

        elif action == "delete":
            arcpy.management.DeleteField(
                in_table=feature_class,
                drop_field=field_name,
            )
            return f"SUCCESS: 字段删除成功\n  要素类: {feature_class}\n  字段名: {field_name}"

        elif action == "alias":
            new_alias = _safe_strip(new_alias) if new_alias else ""
            if not new_alias:
                return "ERROR: alias 操作需要 new_alias 参数"

            arcpy.management.AlterField(
                in_table=feature_class,
                field=field_name,
                new_field_alias=new_alias,
            )
            return f"SUCCESS: 字段别名修改成功\n  要素类: {feature_class}\n  字段名: {field_name}\n  新别名: {new_alias}"

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

    feature_class = params.get("feature_class", "")
    action = params.get("action", "")
    field_name = params.get("field_name")
    field_type = params.get("field_type", "TEXT")
    field_length = params.get("field_length", 254)
    new_alias = params.get("new_alias")

    result = run(feature_class, action, field_name, field_type, field_length, new_alias)

    if result.startswith("SUCCESS:"):
        _proto_success(result[8:].strip())
    else:
        _proto_error(result[7:].strip())


if __name__ == "__main__":
    main()
