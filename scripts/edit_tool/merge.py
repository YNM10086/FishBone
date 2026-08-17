"""
独立脚本：多图层合并 Merge
将多个同类型的要素图层（点/线/面）合并为一个图层。
用法: python merge.py '<json_params>'
"""
import sys
import json
import arcpy
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _utils import normalize, safe_strip
from _protocol import success, error


def main():
    params = json.loads(sys.argv[1])
    inputs_raw = params.get("inputs", "")
    output = params.get("output", "")
    add_source = params.get("add_source", "NO_SOURCE_INFO")
    field_match_mode = params.get("field_match_mode", "AUTOMATIC")

    try:
        if not inputs_raw or not output:
            error("参数缺失：inputs 和 output 均为必填")
            return

        parts = inputs_raw.replace("，", ";").replace("；", ";").split(";")
        inputs = [normalize(p) for p in parts if safe_strip(p)]
        if not inputs:
            error("inputs 解析为空，多个图层请用分号 ; 分隔")
            return
        if len(inputs) < 2:
            error("合并至少需要 2 个输入图层，多个图层请用分号 ; 分隔")
            return

        missing = [p for p in inputs if not arcpy.Exists(p)]
        if missing:
            error(f"输入图层不存在：{' ; '.join(missing)}")
            return

        output = normalize(output)
        out_dir = os.path.dirname(output)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        if add_source not in ("ADD_SOURCE_INFO", "NO_SOURCE_INFO"):
            add_source = "NO_SOURCE_INFO"
        if field_match_mode not in ("AUTOMATIC", "MANUAL_EDIT", "USE_FIRST_SCHEMA"):
            field_match_mode = "AUTOMATIC"

        arcpy.management.Merge(
            inputs=inputs,
            output=output,
            add_source=add_source,
            field_match_mode=field_match_mode,
        )

        if not arcpy.Exists(output):
            error(f"合并无报错但输出未生成：{output}")
            return

        count = int(arcpy.GetCount_management(output).getOutput(0))
        success(
            f"多图层合并完成\n"
            f"  输入图层 ({len(inputs)} 个): {' ; '.join(inputs)}\n"
            f"  输出: {output}\n"
            f"  结果要素数: {count}"
        )
    except arcpy.ExecuteError:
        error(f"多图层合并失败：{arcpy.GetMessages(2)}")
    except Exception as e:
        error(f"多图层合并失败：{str(e)}（异常类型：{type(e).__name__}）")


if __name__ == "__main__":
    main()
