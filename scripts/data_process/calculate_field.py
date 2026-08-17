"""
独立脚本：字段计算 Calculate Field
按预置类型（面积平方米 / 长度米）或自定义 Python 表达式给字段赋值。
示例：
- 面积自动计算: calc_type=面积(平方米) → 自动用 !shape.area@SQUAREMETERS!
- 条件赋值: calc_type=自定义, expression=1 if !shape.area@SQUAREMETERS! > 500 else 0
用法: python calculate_field.py '<json_params>'
"""
import sys
import json
import arcpy
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _utils import normalize, safe_strip
from _protocol import success, error

_PRESETS = {
    "面积(平方米)": "!shape.area@SQUAREMETERS!",
    "长度(米)": "!shape.length@METERS!",
}


def main():
    params = json.loads(sys.argv[1])
    in_table = params.get("in_table", "")
    field = params.get("field", "")
    calc_type = params.get("calc_type", "自定义")
    expression = params.get("expression", "")
    code_block = params.get("code_block", "")

    try:
        if not in_table or not field:
            error("参数缺失：in_table 和 field 均为必填")
            return

        in_table = normalize(in_table)
        field = safe_strip(field)

        if not arcpy.Exists(in_table):
            error(f"要素类/表不存在：{in_table}")
            return

        field_names = [f.name for f in arcpy.ListFields(in_table)]
        if field not in field_names:
            error(f"字段不存在：{field}（可选字段：{'、'.join(field_names[:20])}）")
            return

        # Schema 锁检测（ArcGIS Pro 打开时阻止修改）
        if not arcpy.TestSchemaLock(in_table):
            error(
                "无法获取 Schema 锁，请确认：\n"
                "  1. ArcGIS Pro 中已关闭该要素类的属性表\n"
                "  2. 已从地图中移除该图层\n"
                "  3. 或完全关闭 ArcGIS Pro 后重试"
            )
            return

        if calc_type in _PRESETS:
            expression = _PRESETS[calc_type]
        else:
            calc_type = "自定义"
            if not safe_strip(expression):
                error("calc_type=自定义 时必须提供 expression（如 1 if !字段! > 500 else 0）")
                return

        arcpy.management.CalculateField(
            in_table=in_table,
            field=field,
            expression=expression,
            expression_type="PYTHON3",
            code_block=code_block if safe_strip(code_block) else None,
        )

        # 抽样读取一个计算结果用于反馈
        sample = "（表为空，无样本值）"
        try:
            with arcpy.da.SearchCursor(in_table, [field]) as cursor:
                for row in cursor:
                    sample = f"{row[0]!r}"
                    break
        except Exception:
            pass

        success(
            f"字段计算完成\n"
            f"  要素类/表: {in_table}\n"
            f"  字段: {field}\n"
            f"  计算类型: {calc_type}\n"
            f"  表达式: {expression}\n"
            f"  样本值: {sample}"
        )
    except arcpy.ExecuteError:
        error(f"字段计算失败：{arcpy.GetMessages(2)}")
    except Exception as e:
        error(f"字段计算失败：{str(e)}（异常类型：{type(e).__name__}）")


if __name__ == "__main__":
    main()
